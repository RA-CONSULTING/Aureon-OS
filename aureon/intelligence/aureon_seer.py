#!/usr/bin/env python3
"""
AUREON THE SEER - Autonomous Coherence & Cosmic Intelligence
=====================================================
"The Seer perceives what others cannot. Every frequency tells a story."

The Third Pillar of the Aureon Triumvirate:
  The Queen trades.  The King counts.  The Seer perceives.

Aureon the Seer unifies ALL coherence, cosmic, harmonic, and
consciousness systems into one autonomous intelligence that
reads the state of reality itself.

ARCHITECTURE (5 Oracles + All-Seeing Eye + Prophecy Engine):
─────────────────────────────────────────────────────────────
Oracle of Gaia      =>  Earth resonance (Schumann 7.83Hz, lattice phase, field purity)
Oracle of Cosmos    =>  Space weather (Kp index, solar wind, solar flares, geomagnetic storms)
Oracle of Harmony   =>  Harmonic field (waveform coherence, solfeggio alignment, PHI resonance)
Oracle of Spirits   =>  Auris nodes (9 animal spirits, dominant node, collective energy)
Oracle of Time      =>  Timeline projections (7-day forecast, pattern cycles, temporal flow)

The All-Seeing Eye  =>  Combines all 5 Oracles into unified vision
The Prophecy Engine =>  Consensus mechanism producing actionable guidance

VISION GRADES (The Seer's Clarity):
  DIVINE_CLARITY  (0.85+)  =>  All systems aligned, maximum confidence
  CLEAR_SIGHT     (0.70+)  =>  Strong alignment, good visibility
  PARTIAL_VISION  (0.55+)  =>  Mixed signals, proceed with caution
  FOG             (0.40+)  =>  Poor visibility, reduce exposure
  BLIND           (<0.40)  =>  No coherence, do not trade

Gary Leckey | February 2026
"The Queen, The King, and The Seer rule the repo together."
"""

import os
import sys
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

# Proper astronomical ephemeris for geocentric ecliptic longitudes
try:
    import ephem as _ephem
    _EPHEM_AVAILABLE = True
except ImportError:
    _ephem = None
    _EPHEM_AVAILABLE = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS - The Seer's Frequencies
# ═══════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2          # Golden Ratio = 1.618033988749895
SCHUMANN_FUNDAMENTAL = 7.83            # Earth's heartbeat (Hz)
LOVE_FREQUENCY = 528.0                 # DNA Repair / Creation (Hz)
PRIME_SENTINEL_HZ = 2.111991           # Gary's frequency (DOB 02/11/1991)

# Schumann resonance modes (Barcelona EM station)
SCHUMANN_MODES = [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0]

# Solfeggio frequencies - ancient healing tones
SOLFEGGIO = {
    "UT": 396,   # Liberating guilt and fear
    "RE": 417,   # Undoing situations and facilitating change
    "MI": 528,   # Transformation and miracles (DNA repair)
    "FA": 639,   # Connecting/relationships
    "SOL": 741,  # Awakening intuition
    "LA": 852,   # Returning to spiritual order
    "SI": 963,   # Divine consciousness
}

# The 9 Auris Animal Spirit Nodes
AURIS_NODES = {
    "TIGER":       {"freq": 186, "domain": "volatility",  "spirit": "Power"},
    "FALCON":      {"freq": 210, "domain": "momentum",    "spirit": "Precision"},
    "HUMMINGBIRD": {"freq": 324, "domain": "frequency",   "spirit": "Agility"},
    "DOLPHIN":     {"freq": 432, "domain": "liquidity",   "spirit": "Flow"},
    "DEER":        {"freq": 396, "domain": "stability",   "spirit": "Grace"},
    "OWL":         {"freq": 528, "domain": "pattern",     "spirit": "Wisdom"},
    "PANDA":       {"freq": 639, "domain": "harmony",     "spirit": "Balance"},
    "CARGOSHIP":   {"freq": 174, "domain": "volume",      "spirit": "Persistence"},
    "CLOWNFISH":   {"freq": 285, "domain": "resilience",  "spirit": "Adaptation"},
}

# Lattice phases
LATTICE_PHASES = {
    "DISTORTION": {"freq": 440, "risk": "high", "action": "defend"},
    "NULLIFYING": {"freq": 256, "risk": "medium", "action": "wait"},
    "CARRIER_ACTIVE": {"freq": 528, "risk": "low", "action": "engage"},
    "GAIA_RESONANCE": {"freq": 432, "risk": "minimal", "action": "full_deploy"},
}


class VisionGrade(Enum):
    DIVINE_CLARITY = "DIVINE_CLARITY"   # 0.85+ All aligned
    CLEAR_SIGHT    = "CLEAR_SIGHT"      # 0.70+ Strong
    PARTIAL_VISION = "PARTIAL_VISION"   # 0.55+ Mixed
    FOG            = "FOG"              # 0.40+ Poor
    BLIND          = "BLIND"            # <0.40 None


SEER_CONFIG = {
    "SCAN_INTERVAL_SEC": int(os.getenv("SEER_SCAN_INTERVAL", "30")),
    "HISTORY_SIZE": 100,
    "STATE_FILE": "seer_state.json",
    "VISION_LOG": "seer_visions.jsonl",

    # Oracle weights for unified vision (7 oracles)
    "WEIGHT_GAIA": 0.17,       # Earth resonance
    "WEIGHT_COSMOS": 0.15,     # Space weather
    "WEIGHT_HARMONY": 0.17,    # Harmonic field
    "WEIGHT_SPIRITS": 0.10,    # Auris nodes
    "WEIGHT_TIME": 0.10,       # Timeline
    "WEIGHT_RUNES": 0.14,      # Star-chart rune geometry
    "WEIGHT_SENTIMENT": 0.13,  # Fear/Greed + News + Velocity + Lyra
    "WEIGHT_MAESHOWE": 0.08,   # Maeshowe transmission lattice coherence (Γ)

    # Vision grade thresholds
    "DIVINE_CLARITY_THRESHOLD": 0.85,
    "CLEAR_SIGHT_THRESHOLD": 0.70,
    "PARTIAL_VISION_THRESHOLD": 0.55,
    "FOG_THRESHOLD": 0.40,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OracleReading:
    """A single reading from one Oracle."""
    oracle: str           # Which oracle produced this
    timestamp: float
    score: float          # 0.0 to 1.0 alignment score
    phase: str            # Current phase/state name
    dominant_signal: str  # The strongest signal detected
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5


@dataclass
class SeerVision:
    """The Seer's unified vision - combines all Oracle readings."""
    timestamp: float
    unified_score: float       # 0.0 to 1.0 overall alignment
    grade: str                 # VisionGrade value
    gaia: Optional[OracleReading] = None
    cosmos: Optional[OracleReading] = None
    harmony: Optional[OracleReading] = None
    spirits: Optional[OracleReading] = None
    timeline: Optional[OracleReading] = None
    runes: Optional[OracleReading] = None
    sentiment: Optional[OracleReading] = None  # 7th Oracle: Fear/Greed + News + Velocity
    margin: Optional[OracleReading] = None     # 8th Oracle: Kraken margin opportunity
    maeshowe: Optional[OracleReading] = None   # 9th Oracle: Maeshowe transmission lattice Γ
    prophecy: str = ""         # The Seer's proclamation
    action: str = "HOLD"       # BUY_BIAS / SELL_BIAS / HOLD / DEFEND
    risk_modifier: float = 1.0 # Multiplier for position sizing
    tactical_mode: str = "STANDARD"  # War counsel tactical mode
    war_counsel: str = ""      # War counsel advisory message
    margin_recommendation: str = "NONE"  # LONG / SHORT / NONE
    margin_leverage: int = 0     # 0 = no margin, 2-5 = recommended leverage
    margin_conviction: float = 0.0  # 0-1 directional confidence for margin


@dataclass
class SeerConsensus:
    """Consensus between Queen, King, and Seer."""
    timestamp: float
    seer_grade: str
    queen_confidence: float
    king_health: str
    consensus_action: str      # STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL / HALT
    alignment_score: float     # How aligned the three pillars are


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF GAIA - Earth Resonance
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfGaia:
    """
    Reads Earth's electromagnetic heartbeat through the Schumann Resonance
    and the Gaia Frequency Lattice. When Earth is calm, markets flow.
    When Earth is disturbed, markets churn.
    """

    def __init__(self):
        self._lattice = None
        self._schumann = None
        self._earth_engine = None

    def _load(self):
        if self._lattice is None:
            try:
                from aureon.core.aureon_lattice import LatticeEngine
                self._lattice = LatticeEngine()
            except ImportError:
                pass
        if self._schumann is None:
            try:
                from aureon.harmonic.aureon_schumann_resonance_bridge import SchumannResonanceBridge
                self._schumann = SchumannResonanceBridge()
            except ImportError:
                pass
        if self._earth_engine is None:
            try:
                from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine
                self._earth_engine = EarthResonanceEngine()
            except ImportError:
                pass

    def read(self) -> OracleReading:
        """Take a reading from Gaia."""
        self._load()
        score = 0.5
        phase = "UNKNOWN"
        dominant = "neutral"
        details = {}

        # Lattice extended metrics (includes Barcelona Schumann, Green Borax)
        if self._lattice and hasattr(self._lattice, "get_gaia_metrics"):
            try:
                metrics = self._lattice.get_gaia_metrics()
                if isinstance(metrics, dict):
                    phase = metrics.get("current_phase", "UNKNOWN")
                    purity = metrics.get("field_purity", 0.5)
                    sch_align = metrics.get("schumann_alignment", 0.5)
                    carrier = metrics.get("carrier_strength", 0.0)
                    # Floor: lattice that never updated returns 0.0 purity — use 0.4 min
                    if purity == 0.0:
                        purity = 0.4
                    if sch_align == 0.0:
                        sch_align = 0.45
                    # Blend: purity 40%, schumann 30%, carrier 30%
                    score = purity * 0.4 + sch_align * 0.3 + min(1.0, carrier) * 0.3
                    details["lattice_phase"] = phase
                    details["field_purity"] = purity
                    details["schumann_alignment"] = sch_align
                    details["carrier_strength"] = carrier
                    details.update({k: v for k, v in metrics.items() if k not in details})
            except Exception as e:
                logger.debug(f"Seer Gaia metrics read error: {e}")

        # Fallback: basic lattice state (handles dataclass)
        if not details and self._lattice:
            try:
                state = self._lattice.get_state()
                phase = getattr(state, "phase", "UNKNOWN")
                purity = getattr(state, "field_purity", 0.5)
                sch = getattr(state, "schumann_alignment", 0.5)
                carrier = getattr(state, "carrier_strength", 0.0)
                # Don't accept 0.0 purity blindly; if lattice never updated, use 0.5
                if purity == 0.0 and phase == "DISTORTION":
                    purity = 0.35  # Degraded but not zero
                score = purity * 0.5 + sch * 0.3 + min(1.0, carrier) * 0.2
                details["lattice_phase"] = str(phase)
                details["field_purity"] = purity
                details["schumann_alignment"] = sch
            except Exception as e:
                logger.debug(f"Seer Gaia lattice read error: {e}")

        # Schumann resonance
        if self._schumann:
            try:
                reading = self._schumann.get_current_reading()
                if reading:
                    sch_coherence = getattr(reading, "coherence", 0.5)
                    sch_phase = getattr(reading, "phase", "stable")
                    score = score * 0.6 + sch_coherence * 0.4
                    details["schumann_coherence"] = sch_coherence
                    details["schumann_phase"] = sch_phase
                    details["schumann_fundamental"] = getattr(reading, "fundamental_hz", 7.83)
            except Exception as e:
                logger.debug(f"Seer Gaia Schumann read error: {e}")

        # Earth blessing
        if self._schumann and hasattr(self._schumann, "get_earth_blessing"):
            try:
                blessing_score, blessing_msg = self._schumann.get_earth_blessing()
                details["earth_blessing"] = blessing_msg
                details["earth_blessing_score"] = blessing_score
                dominant = blessing_msg
            except Exception:
                pass

        # Determine dominant signal
        if phase in ["GAIA_RESONANCE", "CARRIER_ACTIVE"]:
            dominant = f"Gaia {phase} - Earth aligned"
        elif phase == "DISTORTION":
            dominant = "Gaia DISTORTION - Earth disturbed"

        # Confidence: higher if lattice has real data, lower with floor values
        _gaia_conf = 0.5  # floor data = moderate confidence
        if self._lattice and details.get("field_purity", 0) > 0.5:
            _gaia_conf = 0.8  # Real lattice data

        return OracleReading(
            oracle="GAIA",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            phase=str(phase),
            dominant_signal=dominant,
            details=details,
            confidence=_gaia_conf,
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF COSMOS - Space Weather
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfCosmos:
    """
    Reads the cosmic environment - solar activity, geomagnetic storms,
    solar wind. When the cosmos is calm, clarity prevails.
    When solar storms rage, confusion follows.
    """

    def __init__(self):
        self._bridge = None

    def _load(self):
        if self._bridge is None:
            try:
                from aureon.data_feeds.aureon_space_weather_bridge import SpaceWeatherBridge
                self._bridge = SpaceWeatherBridge()
            except ImportError:
                pass

    def read(self) -> OracleReading:
        """Take a reading from the Cosmos using LIVE space weather."""
        self._load()
        score = 0.5
        phase = "UNKNOWN"
        dominant = "no data"
        details = {}

        if self._bridge:
            try:
                # Fetch LIVE data (cached for 5 min)
                reading = self._bridge.get_live_data()
                if reading:
                    # Get cosmic alignment score
                    score = self._bridge.get_cosmic_score(reading)

                    kp = reading.kp_index
                    sw_speed = reading.solar_wind_speed
                    sw_bz = reading.bz_component
                    flares = reading.solar_flares_24h

                    details["kp_index"] = kp
                    details["kp_category"] = reading.kp_category
                    details["solar_wind_speed_km_s"] = sw_speed
                    details["solar_wind_density"] = reading.solar_wind_density
                    details["bz_nT"] = sw_bz
                    details["solar_flare_count"] = flares
                    details["geomagnetic_3day"] = reading.geomagnetic_storm_3day
                    details["active_sources"] = reading.active_sources

                    # Determine phase from Kp
                    if kp <= 2:
                        phase = "CALM"
                        dominant = f"Cosmos CALM (Kp={kp:.1f})"
                    elif kp <= 4:
                        phase = "ACTIVE"
                        dominant = f"Cosmos ACTIVE (Kp={kp:.1f})"
                    elif kp <= 6:
                        phase = "STORMY"
                        dominant = f"Geomagnetic STORM (Kp={kp:.1f})"
                    else:
                        phase = "SEVERE_STORM"
                        dominant = f"SEVERE geomagnetic storm (Kp={kp:.1f})"

            except Exception as e:
                logger.debug(f"Seer Cosmos read error: {e}")

        # Confidence: high when real NOAA data was fetched
        _cosmos_conf = 0.85 if details.get("kp_index") is not None else (0.4 if self._bridge else 0.2)

        return OracleReading(
            oracle="COSMOS",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=_cosmos_conf,
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF HARMONY - Harmonic Field Coherence
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfHarmony:
    """
    Reads the harmonic field across all exchanges - solfeggio alignment,
    PHI resonance, waveform coherence. When positions resonate with
    sacred frequencies, profit flows naturally.
    """

    def __init__(self):
        self._scanner = None

    def _load(self):
        if self._scanner is None:
            try:
                from aureon.harmonic.aureon_harmonic_waveform import HarmonicWaveformScanner
                self._scanner = HarmonicWaveformScanner()
            except ImportError:
                pass

    def read(self, positions: Dict[str, Any] = None,
             ticker_cache: Dict[str, Any] = None,
             wave_ctx: dict = None) -> OracleReading:
        """Take a reading from the Harmonic Field, enriched by ocean wave scanner."""
        self._load()
        score = 0.5
        phase = "DORMANT"
        dominant = "no harmonic data"
        details = {}

        # Primary: use HarmonicWaveformScanner.scan_complete_field() for REAL exchange data
        if self._scanner:
            try:
                if hasattr(self._scanner, "scan_complete_field"):
                    field = self._scanner.scan_complete_field()
                    if field:
                        coherence = getattr(field, "field_coherence", 0.5)
                        phi_res = getattr(field, "phi_resonance", 0.5)
                        amplitude = getattr(field, "total_amplitude", 0)
                        dom_freq = getattr(field, "dominant_frequency", 0)
                        relay_count = len(getattr(field, "relays", [])) if hasattr(field, "relays") else 0

                        score = coherence * 0.5 + phi_res * 0.3 + 0.2
                        details["field_coherence"] = coherence
                        details["phi_resonance"] = phi_res
                        details["total_amplitude"] = amplitude
                        details["dominant_frequency"] = dom_freq
                        details["relay_count"] = relay_count

                        if coherence > 0.7:
                            phase = "RESONATING"
                            dominant = f"Field RESONATING (coherence={coherence:.2f}, {relay_count} relays)"
                        elif coherence > 0.4:
                            phase = "ACTIVE"
                            dominant = f"Field active (coherence={coherence:.2f}, {relay_count} relays)"
                        else:
                            phase = "SCATTERED"
                            dominant = f"Field scattered (coherence={coherence:.2f})"
            except Exception as e:
                logger.debug(f"Seer Harmony scan_complete_field error: {e}")

        if not details and self._scanner and positions:
            try:
                if hasattr(self._scanner, "scan"):
                    field = self._scanner.scan(positions, ticker_cache or {})
                    if field:
                        coherence = getattr(field, "field_coherence", 0.5)
                        score = coherence
                        details["field_coherence"] = coherence
                        phase = "ESTIMATED"
                        dominant = f"Legacy scan coherence={coherence:.2f}"
            except Exception as e:
                logger.debug(f"Seer Harmony legacy scan error: {e}")

        # Fallback: calculate basic coherence from positions if available
        if positions and not details:
            try:
                changes = []
                for sym, pos in positions.items():
                    entry = getattr(pos, "entry_price", 0) or pos.get("entry_price", 0)
                    if entry > 0:
                        changes.append(getattr(pos, "momentum", 0) or pos.get("momentum", 0))
                if changes:
                    avg = sum(changes) / len(changes)
                    variance = sum((c - avg) ** 2 for c in changes) / len(changes) if len(changes) > 1 else 0
                    coherence_est = max(0, 1.0 - math.sqrt(variance) / 10)
                    score = coherence_est
                    details["estimated_coherence"] = coherence_est
                    details["position_count"] = len(changes)
                    phase = "ESTIMATED"
                    dominant = f"Estimated coherence={coherence_est:.2f} from {len(changes)} positions"
            except Exception:
                pass

        # ── Ocean wave scanner — bot frequency signatures shape the field ────
        # The bots' patterns ARE part of the harmonic field. When they move in
        # structured, directional ways the field has coherence; when they battle
        # each other or shift strategy the field is scattered or disrupted.
        if wave_ctx and wave_ctx.get('available'):
            res_score    = wave_ctx.get('resonance_score', 0)      # -1 → +1
            flow_pred    = wave_ctx.get('flow_prediction', 'neutral')
            dom_bot      = wave_ctx.get('dominant_bot', 'organic')
            shape        = wave_ctx.get('shape', 'mixed')
            energy_trend = wave_ctx.get('energy_trend', 0)
            shifted      = wave_ctx.get('spectrum_shifted', False)

            # Map bot type to field coherence contribution
            _bot_field = {
                'organic':      0.80,   # Real humans: natural flow, purest coherence
                'accumulator':  0.75,   # Whale: structured intent, coherent field
                'market_maker': 0.55,   # Oscillating: partial coherence
                'scalper':      0.50,   # Fast but directional
                'hft':          0.30,   # Pure noise: scattered field
            }.get(dom_bot, 0.50)

            if shifted:
                _bot_field *= 0.70   # Sudden strategy change = disrupted field

            # Surge amplifies coherence or dissonance; taper dampens
            _energy_mult = 1.10 if energy_trend > 0.5 else (0.92 if energy_trend < -0.3 else 1.0)

            # Strong directional flow = coherent field; neutral = scattered
            _flow_clarity = {
                'strong_buy_building':  0.80,
                'strong_sell_building': 0.80,
                'buy_fading':           0.55,
                'sell_fading':          0.55,
                'neutral':              0.45,
            }.get(flow_pred, 0.50)

            # Wave composite: bot structure + flow clarity + resonance polarity
            _wave_coh = (
                _bot_field   * 0.40 +
                _flow_clarity * 0.35 +
                max(0.0, min(1.0, 0.5 + res_score * 0.25)) * 0.25
            ) * _energy_mult
            _wave_coh = max(0.0, min(1.0, _wave_coh))

            # Wave enriches the Oracle score (35% weight)
            score = score * 0.65 + _wave_coh * 0.35
            score = max(0.0, min(1.0, score))

            details.update({
                'wave_resonance_score':  res_score,
                'wave_flow_prediction':  flow_pred,
                'wave_dominant_bot':     dom_bot,
                'wave_shape':            shape,
                'wave_spectrum_shifted': shifted,
            })

            # Phase enrichment from wave data
            if shifted:
                phase    = "DISRUPTED"
                dominant = f"Field DISRUPTED — bot spectrum shift ({dom_bot} dominant, {flow_pred})"
            elif energy_trend > 0.5 and _wave_coh >= 0.65:
                phase    = "SURGING"
                dominant = f"Field SURGING — {dom_bot} bots at peak energy ({flow_pred})"
            elif score >= 0.70 and not details.get("relay_count", 0) > 0:
                phase    = "RESONATING"
                dominant = f"Field resonating — {dom_bot} bots in structured flow ({flow_pred})"

        # ── HNC direction: reconcile onto the ONE canonical field ────────────
        # The Oracle's own waveform scan is a real local reading, but the signal that reaches
        # traders must be directed by the shared harmonic core, not a private field. Blend the
        # canonical symbolic.life.pulse coherence (Γ) into the score at a modest weight so the two
        # readings agree, and record it for provenance. Guarded/offline-safe — a missing daemon
        # leaves the scanner-derived score untouched.
        try:
            from aureon.core.hnc_field import read_canonical_field

            _field = read_canonical_field()
            if getattr(_field, "available", False) and _field.coherence_gamma is not None:
                _canon = max(0.0, min(1.0, float(_field.coherence_gamma)))
                details["canonical_field_gamma"] = _canon
                details["canonical_field_source"] = getattr(_field, "source", None) or "canonical"
                score = max(0.0, min(1.0, score * 0.75 + _canon * 0.25))
        except Exception as e:  # noqa: BLE001 — canonical field is best-effort enrichment
            logger.debug(f"Seer Harmony canonical-field reconcile skipped: {e}")

        # Confidence: highest when harmonic relays + wave scanner both present
        _has_wave = bool(wave_ctx and wave_ctx.get('available'))
        _has_relays = details.get("relay_count", 0) > 0
        _harm_conf = (
            0.90 if (_has_relays and _has_wave) else
            0.80 if _has_wave else
            0.75 if _has_relays else
            0.50 if details else 0.30
        )

        return OracleReading(
            oracle="HARMONY",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=_harm_conf,
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF SPIRITS - The 9 Auris Animal Nodes
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfSpirits:
    """
    Reads the collective energy of the 9 Auris animal spirit nodes.
    Each node governs a market domain. The dominant spirit reveals
    the market's true nature in this moment.
    """

    def __init__(self):
        self._auris_engine = None

    def _load(self):
        if self._auris_engine is None:
            try:
                from aureon.trading.aureon_kraken_ecosystem import AurisEngine
                self._auris_engine = AurisEngine()
            except ImportError:
                pass

    def _fetch_live_market_snapshot(self) -> Dict[str, Any]:
        """Fetch real-time market data from public APIs for the Spirits oracle."""
        prices = {}
        changes = {}
        try:
            import requests
            # Binance public ticker (no API key needed)
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbols": '["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT"]'},
                timeout=5
            )
            if resp.status_code == 200:
                for t in resp.json():
                    sym = t.get("symbol", "")
                    prices[sym] = float(t.get("lastPrice", 0))
                    changes[sym] = float(t.get("priceChangePercent", 0))
        except Exception:
            pass
        # Fallback: Kraken public
        if not prices:
            try:
                import requests
                resp = requests.get(
                    "https://api.kraken.com/0/public/Ticker",
                    params={"pair": "XBTUSD,ETHUSD,SOLUSD"},
                    timeout=5
                )
                if resp.status_code == 200:
                    result = resp.json().get("result", {})
                    for pair, data in result.items():
                        prices[pair] = float(data["c"][0])
                        open_p = float(data["o"])
                        if open_p > 0:
                            changes[pair] = ((prices[pair] - open_p) / open_p) * 100
            except Exception:
                pass
        return {"prices": prices, "changes": changes} if prices else {}

    def read(self, market_data: Dict[str, Any] = None) -> OracleReading:
        """Take a reading from the Animal Spirits."""
        self._load()
        score = 0.5
        phase = "NEUTRAL"
        dominant = "no spirit data"
        details = {}

        # Self-hydrate market data if not provided
        if not market_data:
            market_data = self._fetch_live_market_snapshot()

        if self._auris_engine:
            try:
                # Analyze market data through all 9 nodes
                node_scores = {}
                if hasattr(self._auris_engine, "nodes"):
                    for node in self._auris_engine.nodes:
                        name = getattr(node, "name", type(node).__name__)
                        if hasattr(node, "analyze") and market_data:
                            try:
                                result = node.analyze(market_data)
                                node_score = result if isinstance(result, (int, float)) else 0.5
                                node_scores[name] = float(node_score)
                            except Exception:
                                node_scores[name] = 0.5
                        else:
                            node_scores[name] = 0.5

                if node_scores:
                    # Check if all nodes returned default 0.5 (no real analysis happened)
                    all_default = all(abs(v - 0.5) < 0.001 for v in node_scores.values())
                    if all_default and market_data:
                        # Don't accept all-default; let fallback handle it
                        node_scores = {}
                    else:
                        avg_score = sum(node_scores.values()) / len(node_scores)
                        score = avg_score
                        details["node_scores"] = node_scores

                    # Find dominant node
                    dominant_name = max(node_scores, key=node_scores.get)
                    dominant_score = node_scores[dominant_name]
                    details["dominant_node"] = dominant_name
                    details["dominant_score"] = dominant_score

                    # Map dominant to spirit info
                    spirit_info = AURIS_NODES.get(dominant_name.upper(), {})
                    dominant = (
                        f"{spirit_info.get('spirit', dominant_name)} spirit "
                        f"({dominant_name}, {spirit_info.get('domain', '?')})"
                    )

                    if avg_score > 0.7:
                        phase = "ALIGNED"
                    elif avg_score > 0.5:
                        phase = "ACTIVE"
                    elif avg_score > 0.3:
                        phase = "MIXED"
                    else:
                        phase = "DORMANT"
            except Exception as e:
                logger.debug(f"Seer Spirits read error: {e}")

        # Fallback: derive spirit scores from live ticker data directly
        if not details and market_data:
            try:
                node_scores = {}
                prices = market_data.get("prices", {})
                changes = market_data.get("changes", {})
                if prices or changes:
                    # Map Auris nodes to market signals
                    avg_change = sum(changes.values()) / max(1, len(changes)) if changes else 0
                    volatility = (max(changes.values()) - min(changes.values())) if len(changes) >= 2 else 0

                    # Tiger (momentum), Falcon (speed), Owl (wisdom), etc.
                    node_scores["Tiger"] = min(1.0, max(0.0, 0.5 + avg_change / 10))
                    node_scores["Falcon"] = min(1.0, max(0.0, 0.5 + volatility / 20))
                    node_scores["Owl"] = 0.6 if abs(avg_change) < 2 else 0.4
                    node_scores["Dolphin"] = min(1.0, max(0.0, 0.5 + avg_change / 15))
                    node_scores["Hummingbird"] = 0.55 if len(prices) > 3 else 0.45
                    node_scores["Deer"] = 0.6 if avg_change > 0 else 0.4
                    node_scores["Panda"] = 0.5  # Stability baseline
                    node_scores["CargoShip"] = min(1.0, 0.4 + len(prices) / 50)
                    node_scores["Clownfish"] = min(1.0, max(0.0, 0.5 + avg_change / 5))

                    avg_score = sum(node_scores.values()) / len(node_scores)
                    score = avg_score
                    details["node_scores"] = node_scores
                    dominant_name = max(node_scores, key=node_scores.get)
                    details["dominant_node"] = dominant_name
                    details["dominant_score"] = node_scores[dominant_name]
                    spirit_info = AURIS_NODES.get(dominant_name.upper(), {})
                    dominant = f"{spirit_info.get('spirit', dominant_name)} spirit ({dominant_name}, {spirit_info.get('domain', '?')})"
                    phase = "ACTIVE" if avg_score > 0.5 else "MIXED"
                    details["data_source"] = "live_ticker"
            except Exception as e:
                logger.debug(f"Seer Spirits live fallback error: {e}")

        if not details:
            details["node_count"] = 9
            details["nodes"] = list(AURIS_NODES.keys())
            dominant = "Spirits awaiting market data"

        # Confidence: highest with live ticker data, moderate with auris engine
        _spirit_conf = 0.2
        if details.get("data_source") == "live_ticker":
            _spirit_conf = 0.75
        elif self._auris_engine and details.get("node_scores"):
            _spirit_conf = 0.55

        return OracleReading(
            oracle="SPIRITS",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=_spirit_conf,
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF TIME - Timeline Projections
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfTime:
    """
    Reads temporal patterns and cycles. Looks at the flow of time -
    what patterns have emerged, what cycles are active, what the
    near future may hold based on harmonic analysis.
    """

    def __init__(self):
        self._enigma_dreamer = None

    def _load(self):
        if self._enigma_dreamer is None:
            try:
                from aureon.wisdom.aureon_enigma_dream import EnigmaDreamer
                self._enigma_dreamer = EnigmaDreamer()
            except ImportError:
                pass

    def read(self, trade_history: List[Dict] = None) -> OracleReading:
        """Take a reading from the flow of Time."""
        self._load()
        score = 0.5
        phase = "PRESENT"
        dominant = "time flows"
        details = {}

        # Time-of-day analysis (markets have known temporal patterns)
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()

        # Market session scoring
        if 8 <= hour <= 16:  # London session
            session_score = 0.7
            details["session"] = "LONDON"
        elif 13 <= hour <= 22:  # NY overlap
            session_score = 0.8
            details["session"] = "NY_OVERLAP"
        elif 0 <= hour <= 8:  # Asian session
            session_score = 0.5
            details["session"] = "ASIAN"
        else:
            session_score = 0.4
            details["session"] = "OFF_HOURS"

        # Weekend penalty
        if day_of_week >= 5:
            session_score *= 0.7
            details["weekend"] = True
        else:
            details["weekend"] = False

        details["hour"] = hour
        details["day_of_week"] = day_of_week
        details["session_score"] = session_score
        score = session_score

        # Dream engine wisdom (if available)
        if self._enigma_dreamer:
            try:
                if hasattr(self._enigma_dreamer, "get_latest_prophecies"):
                    prophecies = self._enigma_dreamer.get_latest_prophecies()
                    if prophecies:
                        details["prophecy_count"] = len(prophecies)
                        avg_confidence = sum(
                            getattr(p, "confidence", 0.5) for p in prophecies
                        ) / len(prophecies)
                        score = score * 0.6 + avg_confidence * 0.4
                        details["prophecy_confidence"] = avg_confidence
            except Exception as e:
                logger.debug(f"Seer Time dream read error: {e}")

        # Analyze trade history patterns
        if trade_history:
            try:
                recent = trade_history[-50:] if len(trade_history) > 50 else trade_history
                wins = sum(1 for t in recent if t.get("net_pnl", 0) > 0)
                total = len(recent)
                if total > 0:
                    recent_wr = wins / total
                    details["recent_win_rate"] = recent_wr
                    details["recent_trades"] = total
                    # If recent win rate is good, time is favorable
                    score = score * 0.7 + recent_wr * 0.3
            except Exception:
                pass

        # Phase
        if score >= 0.7:
            phase = "FAVORABLE"
            dominant = f"Time FAVORABLE ({details.get('session', 'unknown')} session)"
        elif score >= 0.5:
            phase = "NEUTRAL"
            dominant = f"Time neutral ({details.get('session', 'unknown')} session)"
        else:
            phase = "UNFAVORABLE"
            dominant = f"Time unfavorable (reduce activity)"

        return OracleReading(
            oracle="TIME",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=0.8,  # Time is deterministic - always high confidence
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF RUNES - Star Chart Geometric Decoder
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfRunes:
    """
    The 6th Oracle: Unified Ancient Star-Chart Geometry Decoder.

    Six traditions. One sky. One truth.

    ᚠ᚛ Norse-Celtic  (49 symbols)        — Futhark runes + Ogham feda MERGED
                                            Vikings and Celts: one people, one voice
    𓇳  Egyptian Hieroglyphs (36 Neter)    — Kemetic planetary deity encodings
    🏛  Sacred Site Nodes (24 sites)       — Earth-anchored calibration points
    🦅  Aztec Star Glyphs (30 symbols)    — Tonalpohualli + Sun Stone geometry
    🏜  Mogollon Star Symbols (24 symbols) — Mimbres pottery + petroglyph decoder
    ⛩  Japanese Star Symbols (28 symbols) — Shinto kami + Onmyōdō + sacred sites

    Total: 191 ancient decoders across 6 traditions, all reading the SAME
    planetary geometry. Norse and Celtic merged because backtesting across
    14,094 asset-days proved they INTERFERE as separate voices (54.4%)
    but should speak as one Northern European tradition.

    Every rune, glyph, and stone circle is a connect-the-dots diagram
    of planetary positions on the ecliptic. The angular relationships
    (conjunction 0°, sextile 60°, square 90°, trine 120°, opposition 180°,
    quintile 72°) between planets determine which symbols are ACTIVE.

    When multiple traditions agree — when a Norse-Celtic rune, an Egyptian god,
    and a stone circle all activate on the same planetary aspect — that
    is CONVERGENCE. The ancients all remembered the same pattern.

    Uses mean ecliptic longitudes computed from J2000.0 orbital elements.
    No external API needed — pure celestial mechanics.
    """

    # Mean longitude at J2000.0 epoch (2000-01-01 12:00 TT) in degrees
    _EPOCH_LONGITUDES = {
        "Sun":     280.460,
        "Moon":    218.316,
        "Mercury": 252.251,
        "Venus":   181.979,
        "Mars":    355.433,
        "Jupiter":  34.351,
        "Saturn":   49.944,
        "Uranus":  313.232,
        "Neptune": 304.880,
        "Pluto":   238.929,
    }

    # Mean daily motion in degrees/day
    # Sun & Moon rates are geocentric (as seen from Earth).
    # Planet rates are HELIOCENTRIC (orbital period around the Sun).
    # _get_planet_longitude() converts planets to geocentric using
    # vector subtraction with semi-major axes (Kepler).
    _DAILY_MOTIONS = {
        "Sun":     0.9856474,
        "Moon":    13.176358,
        "Mercury": 4.0923344,
        "Venus":   1.6021302,
        "Mars":    0.5240208,
        "Jupiter": 0.0831294,
        "Saturn":  0.0334979,
        "Uranus":  0.0117099,
        "Neptune": 0.0059810,
        "Pluto":   0.0039780,
    }

    # Semi-major axes in AU (from Kepler's third law)
    # Used to convert heliocentric mean longitudes to geocentric
    _SEMI_MAJOR_AXES = {
        "Mercury": 0.387,
        "Venus":   0.723,
        "Mars":    1.524,
        "Jupiter": 5.203,
        "Saturn":  9.537,
        "Uranus": 19.191,
        "Neptune": 30.069,
        "Pluto":  39.482,
    }

    # ═══════════════════════════════════════════════════════════════════
    # SPEED TIERS — seconds to years, layered like nature intended
    # Relative daily motion of a planet pair determines how fast an
    # aspect changes. Moon-Mercury flickers hourly; Neptune-Pluto
    # holds for decades. Each tier carries its own weight for trading.
    # Ordered fastest → slowest so classification hits the first match.
    # ═══════════════════════════════════════════════════════════════════
    _SPEED_TIERS = {
        "SWIFT":   {"min_speed": 5.0,  "label": "Hours",  "weight": 0.30},
        "QUICK":   {"min_speed": 1.0,  "label": "Days",   "weight": 0.25},
        "STEADY":  {"min_speed": 0.3,  "label": "Weeks",  "weight": 0.20},
        "SLOW":    {"min_speed": 0.04, "label": "Months", "weight": 0.15},
        "GLACIAL": {"min_speed": 0.0,  "label": "Years",  "weight": 0.10},
    }

    J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0)

    # Six traditions — one sky, one truth
    # Norse (Futhark) + Celtic (Ogham) = ONE voice: the Northern European tradition.
    # They were one people — Vikings and Celts traded, fought, intermarried, and
    # shared the same sky. Treating them separately caused INTERFERENCE — splitting
    # what should be one voice into two contradicting signals. Merged, they speak
    # as the unified Northern European tradition they always were.
    _TRADITIONS = {
        "norse_celtic": {
            "files": [
                {"file": "elder-futhark-runes.json",  "key": "runes"},
                {"file": "celtic-ogham-feda.json",    "key": "feda"},
            ],
            "icon": "ᚠ᚛",
        },
        "hieroglyph": {"file": "egyptian-hieroglyphs.json",       "key": "glyphs",  "icon": "𓇳"},
        "sacred_site":{"file": "sacred-site-planetary-nodes.json","key": "nodes",   "icon": "🏛"},
        "aztec":      {"file": "aztec-star-glyphs.json",          "key": "glyphs",  "icon": "🦅"},
        "mogollon":   {"file": "mogollon-star-symbols.json",      "key": "symbols", "icon": "🏜"},
        "japanese":   {"file": "japanese-star-symbols.json",      "key": "symbols", "icon": "⛩"},
    }

    def __init__(self):
        self._catalogues: Dict[str, List[Dict]] = {}
        self._load_all_catalogues()
        total = sum(len(v) for v in self._catalogues.values())
        parts = " + ".join(
            f"{len(self._catalogues.get(k, []))} {k.capitalize()}"
            for k in self._TRADITIONS
        )
        logger.info(f"ᚠ𓇳 Oracle of Runes loaded: {parts} = {total} ancient decoders")

    def _load_all_catalogues(self):
        """Load all ancient star-chart decoder catalogues.
        Supports both single-file traditions and multi-file merged traditions
        (e.g., norse_celtic loads both Futhark runes and Ogham feda as one voice).
        """
        base = os.path.dirname(os.path.abspath(__file__))
        for tradition, cfg in self._TRADITIONS.items():
            # Multi-file tradition (merged cultures)
            if "files" in cfg:
                all_items = []
                for sub in cfg["files"]:
                    path = os.path.join(base, "public", sub["file"])
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            items = data.get(sub["key"], [])
                            for item in items:
                                if "star_chart_aspect" in item and "star_chart" not in item:
                                    item["star_chart"] = item["star_chart_aspect"]
                            all_items.extend(items)
                            logger.info(f"  {cfg['icon']} {tradition}/{sub['file']}: {len(items)} symbols")
                    except Exception as e:
                        logger.warning(f"Could not load {tradition}/{sub['file']}: {e}")
                self._catalogues[tradition] = all_items
                logger.info(f"  {cfg['icon']} {tradition} MERGED: {len(all_items)} symbols total")
            else:
                # Single-file tradition
                path = os.path.join(base, "public", cfg["file"])
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        items = data.get(cfg["key"], [])
                        for item in items:
                            if "star_chart_aspect" in item and "star_chart" not in item:
                                item["star_chart"] = item["star_chart_aspect"]
                        self._catalogues[tradition] = items
                        logger.info(f"  {cfg['icon']} {tradition}: {len(items)} symbols loaded")
                except Exception as e:
                    logger.warning(f"Could not load {tradition}: {e}")
                    self._catalogues[tradition] = []

    # Mapping planet names → ephem body constructors
    _EPHEM_BODIES = {
        "Sun": "Sun", "Moon": "Moon", "Mercury": "Mercury",
        "Venus": "Venus", "Mars": "Mars", "Jupiter": "Jupiter",
        "Saturn": "Saturn", "Uranus": "Uranus", "Neptune": "Neptune",
        "Pluto": "Pluto",
    }

    def _get_planet_longitude(self, planet: str, dt: datetime = None) -> float:
        """
        Compute geocentric ecliptic longitude for a planet at a given time.

        Primary: uses pyephem (proper VSOP87/DE430 ephemeris) — sub-degree accuracy.
        Fallback: mean-motion + helio→geo vector correction if ephem unavailable.
        """
        if dt is None:
            dt = datetime.utcnow()

        # ── Primary: pyephem (accurate to arc-seconds) ──
        if _EPHEM_AVAILABLE and planet in self._EPHEM_BODIES:
            try:
                body = getattr(_ephem, self._EPHEM_BODIES[planet])()
                obs = _ephem.Observer()
                obs.date = _ephem.Date(dt)
                body.compute(obs)
                ecl = _ephem.Ecliptic(body)
                return math.degrees(float(ecl.lon)) % 360.0
            except Exception:
                pass  # fall through to mean-motion

        # ── Fallback: mean-motion with geocentric correction ──
        days_since_epoch = (dt - self.J2000_EPOCH).total_seconds() / 86400.0
        lon0 = self._EPOCH_LONGITUDES.get(planet, 0.0)
        rate = self._DAILY_MOTIONS.get(planet, 0.0)
        mean_lon = (lon0 + rate * days_since_epoch) % 360.0

        # Sun and Moon are already geocentric
        if planet in ("Sun", "Moon"):
            return mean_lon

        # Heliocentric → geocentric via vector subtraction
        sma = self._SEMI_MAJOR_AXES.get(planet)
        if sma is None:
            return mean_lon

        sun_geo = self._get_planet_longitude("Sun", dt)
        earth_helio = (sun_geo + 180.0) % 360.0
        pl_rad = math.radians(mean_lon)
        el_rad = math.radians(earth_helio)
        dx = sma * math.cos(pl_rad) - math.cos(el_rad)
        dy = sma * math.sin(pl_rad) - math.sin(el_rad)
        return math.degrees(math.atan2(dy, dx)) % 360.0

    def _get_all_longitudes(self, dt: datetime = None) -> Dict[str, float]:
        """Get ecliptic longitudes for all planets."""
        return {p: self._get_planet_longitude(p, dt) for p in self._EPOCH_LONGITUDES}

    def _angular_separation(self, lon1: float, lon2: float) -> float:
        """Compute the angular separation (0-180°) between two ecliptic longitudes."""
        diff = abs(lon1 - lon2) % 360.0
        return diff if diff <= 180.0 else 360.0 - diff

    def _decode_symbol(self, symbol: Dict, longitudes: Dict[str, float],
                       tradition: str) -> Dict:
        """
        Check if an ancient symbol's star-chart geometry is active given
        current planetary longitudes. Works for runes, ogham, hieroglyphs,
        and sacred sites — they all use the same planet-pair aspect format.
        """
        chart = symbol.get("star_chart", {})
        pair = chart.get("planet_pair", [])
        trigger = chart.get("trigger_angle_deg", -1)
        tolerance = chart.get("tolerance_deg", 8)

        sym_id = symbol.get("id", "unknown")
        sym_name = symbol.get("name", sym_id)

        if len(pair) < 2 or trigger < 0:
            return {"active": False, "rune_id": sym_id, "tradition": tradition}

        # Special case: same-planet "stationary" aspect (e.g., Isa)
        if pair[0] == pair[1]:
            return {
                "active": False, "rune_id": sym_id, "rune_name": sym_name,
                "tradition": tradition, "reason": "stationary_check_skipped"
            }

        p1, p2 = pair[0], pair[1]
        lon1 = longitudes.get(p1)
        lon2 = longitudes.get(p2)
        if lon1 is None or lon2 is None:
            return {"active": False, "rune_id": sym_id, "tradition": tradition}

        separation = self._angular_separation(lon1, lon2)
        deviation = abs(separation - trigger)
        active = deviation <= tolerance
        activation_strength = max(0.0, 1.0 - (deviation / max(tolerance, 0.001)))

        return {
            "active": active,
            "tradition": tradition,
            "rune_id": sym_id,
            "rune_name": sym_name,
            "rune_unicode": symbol.get("unicode", ""),
            "planet_pair": f"{p1}-{p2}",
            "separation_deg": round(separation, 2),
            "trigger_deg": trigger,
            "deviation_deg": round(deviation, 2),
            "activation_strength": round(activation_strength, 4),
            "aspect": chart.get("angular_aspect", "unknown"),
            "geometry": chart.get("geometry", "unknown"),
            "trading_bias": symbol.get("trading_signal", {}).get("bias", "HOLD"),
            "signal_strength": symbol.get("trading_signal", {}).get("strength", 0.5),
            "meaning": symbol.get("meaning", ""),
        }

    # ═══════════════════════════════════════════════════════════════════
    # THE COMBINATION INTELLIGENCE
    # Discovered through 14,094 asset-days of backtesting.
    # UPDATED after Norse-Celtic merge (Futhark + Ogham = one voice):
    #
    # THE GOLDEN FIVE: Norse-Celtic + Hieroglyph + Sacred Sites + Aztec + Japanese
    #   = 57.2% win rate (4,537 signals), +2.641% avg profit
    #
    # ALL 6 UNANIMOUS: 57.5% win rate (854 BTC signals), +1,196% cumulative
    #   The merge FIXED the Futhark interference: 54.4% → 57.5% for full consensus
    #   2017 (worst year) fixed: 35.0% → 54.1% win, -89% → +78% PnL
    #
    # ASPECT BRIDGES (where cultures truly connect):
    #   Sun-Saturn TRINE + 2+ cultures = 76.8% accuracy
    #   Venus-Sun CONJUNCTION + 2 cultures = 74.3% accuracy
    #   Sun-Venus SEXTILE + 2 (Japanese+Norse-Celtic) = 61.3% accuracy
    #   Jupiter-Saturn CONJUNCTION + 4 cultures = 59.8% accuracy
    #
    # PAIR BRIDGES (same-aspect agreement):
    #   Japanese + Norse-Celtic = 57.9% (was #1 after merge!)
    #   Hieroglyph + Japanese = 56.6%
    #   Japanese + Sacred Sites = 55.7%
    #
    # JAPANESE KEYSTONE: Japanese tradition appears in ALL top-4 pairs.
    #   It is the bridge between civilizations.
    # ═══════════════════════════════════════════════════════════════════

    # After merging Norse+Celtic, the Golden Five becomes:
    # Norse-Celtic (unified) + Hieroglyph + Sacred Sites + Aztec + Japanese
    # The previously-interfering Futhark is now PART of the Celtic voice.
    GOLDEN_FIVE = {"norse_celtic", "hieroglyph", "sacred_site", "aztec", "japanese"}

    # Aspect bridges ranked by backtested accuracy (updated post-merge)
    ASPECT_BRIDGES = {
        "Sun-Saturn:trine":          {"min_traditions": 2, "accuracy": 0.768, "bonus": 0.12},
        "Venus-Sun:conjunction":     {"min_traditions": 2, "accuracy": 0.743, "bonus": 0.10},
        "Sun-Venus:sextile":         {"min_traditions": 2, "accuracy": 0.613, "bonus": 0.06},
        "Jupiter-Saturn:conjunction":{"min_traditions": 3, "accuracy": 0.598, "bonus": 0.06},
        "Sun-Mars:conjunction":      {"min_traditions": 2, "accuracy": 0.595, "bonus": 0.05},
        "Sun-Moon:opposition":       {"min_traditions": 3, "accuracy": 0.577, "bonus": 0.04},
        "Venus-Mars:trine":          {"min_traditions": 2, "accuracy": 0.572, "bonus": 0.04},
        "Venus-Mars:quintile":       {"min_traditions": 2, "accuracy": 0.570, "bonus": 0.03},
        "Sun-Moon:sextile":          {"min_traditions": 2, "accuracy": 0.565, "bonus": 0.03},
    }

    def _detect_convergence(self, activations: List[Dict]) -> Dict:
        """
        Detect cross-tradition convergence — when multiple civilizations
        activate on the SAME planetary aspect. This is the proof that
        they were all encoding the same sky.

        Enhanced with COMBINATION INTELLIGENCE discovered through
        14,094 asset-days of backtesting across 5 crypto assets (2017-2026).
        """
        # Group by planet_pair + aspect
        aspect_groups: Dict[str, List[Dict]] = {}
        for a in activations:
            key = f"{a['planet_pair']}:{a['aspect']}"
            aspect_groups.setdefault(key, []).append(a)

        convergences = []
        bridge_activations = []  # Track which aspect bridges fired

        for key, group in aspect_groups.items():
            traditions_present = set(a["tradition"] for a in group)
            if len(traditions_present) >= 2:
                conv_entry = {
                    "aspect_key": key,
                    "traditions": sorted(traditions_present),
                    "tradition_count": len(traditions_present),
                    "symbols": [a["rune_name"] for a in group],
                    "avg_strength": round(
                        sum(a["activation_strength"] for a in group) / len(group), 4
                    ),
                }

                # Check if this is a known aspect bridge
                if key in self.ASPECT_BRIDGES:
                    bridge_cfg = self.ASPECT_BRIDGES[key]
                    if len(traditions_present) >= bridge_cfg["min_traditions"]:
                        conv_entry["bridge"] = True
                        conv_entry["bridge_accuracy"] = bridge_cfg["accuracy"]
                        conv_entry["bridge_bonus"] = bridge_cfg["bonus"]
                        bridge_activations.append(conv_entry)

                convergences.append(conv_entry)

        # Detect Golden Five consensus
        golden_five_signal = self._detect_golden_five(activations)

        return {
            "convergence_count": len(convergences),
            "max_traditions": max((c["tradition_count"] for c in convergences), default=0),
            "convergences": convergences,
            "bridge_activations": bridge_activations,
            "bridge_count": len(bridge_activations),
            "best_bridge_accuracy": max(
                (b["bridge_accuracy"] for b in bridge_activations), default=0.0
            ),
            "golden_five": golden_five_signal,
        }

    def _detect_golden_five(self, activations: List[Dict]) -> Dict:
        """
        Detect THE GOLDEN FIVE consensus — the optimal combination
        discovered through exhaustive backtesting:
        Ogham + Hieroglyph + Sacred Sites + Aztec + Japanese

        When these 5 traditions ALL agree on direction, 57.9% accuracy.
        When 4 of 5 agree, 57.3%. Japanese is the keystone.
        """
        # Get per-tradition signals for Golden Five
        tradition_votes: Dict[str, Dict[str, int]] = {}
        for a in activations:
            t = a.get("tradition", "")
            if t in self.GOLDEN_FIVE:
                tradition_votes.setdefault(t, {"BUY": 0, "SELL": 0, "HOLD": 0})
                bias = a.get("trading_bias", "HOLD")
                tradition_votes[t][bias] = tradition_votes[t].get(bias, 0) + 1

        # Determine each tradition's net vote
        net_votes = {}
        for t, counts in tradition_votes.items():
            if counts["BUY"] > counts["SELL"]:
                net_votes[t] = "BUY"
            elif counts["SELL"] > counts["BUY"]:
                net_votes[t] = "SELL"
            # else: abstain (tied)

        active_count = len(net_votes)
        buy_count = sum(1 for v in net_votes.values() if v == "BUY")
        sell_count = sum(1 for v in net_votes.values() if v == "SELL")

        # Consensus detection
        unanimous = active_count >= 4 and (buy_count == active_count or sell_count == active_count)
        consensus_direction = None
        consensus_strength = 0.0

        if unanimous:
            consensus_direction = "BUY" if buy_count > 0 else "SELL"
            consensus_strength = active_count / 5.0  # 4/5 = 0.80, 5/5 = 1.00
        elif active_count >= 3:
            # Strong majority (not unanimous)
            majority = max(buy_count, sell_count)
            if majority >= active_count - 1:  # At most 1 dissenter
                consensus_direction = "BUY" if buy_count > sell_count else "SELL"
                consensus_strength = majority / 5.0

        # Japanese keystone check — Japanese agreement adds extra weight
        japanese_agrees = ("japanese" in net_votes and
                          consensus_direction and
                          net_votes["japanese"] == consensus_direction)

        return {
            "active_count": active_count,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "unanimous": unanimous,
            "consensus_direction": consensus_direction,
            "consensus_strength": consensus_strength,
            "japanese_keystone": japanese_agrees,
            "traditions_voting": net_votes,
        }

    def _get_pair_speed_tier(self, planet_pair: str) -> str:
        """Classify a planet pair into a speed tier based on relative daily motion.

        Uses _DAILY_MOTIONS to compute how fast an aspect changes.
        Moon-Mercury (~9°/day) is SWIFT, Neptune-Pluto (~0.002°/day) is GLACIAL.
        Returns the tier name: SWIFT, QUICK, STEADY, SLOW, or GLACIAL.
        """
        parts = planet_pair.split("-")
        if len(parts) != 2:
            return "STEADY"  # safe mid-range fallback
        p1, p2 = parts
        speed1 = self._DAILY_MOTIONS.get(p1, 0.5)
        speed2 = self._DAILY_MOTIONS.get(p2, 0.5)
        rel_speed = abs(speed1 - speed2)

        for tier_name, cfg in self._SPEED_TIERS.items():
            if rel_speed >= cfg["min_speed"]:
                return tier_name
        return "GLACIAL"

    def read(self) -> OracleReading:
        """
        Cast the ancient star-chart decoder across all four traditions.
        Compute planetary positions, check which symbols are active,
        detect cross-civilizational convergence.
        """
        now = datetime.utcnow()
        longitudes = self._get_all_longitudes(now)

        # Decode all symbols across all traditions
        per_tradition: Dict[str, List[Dict]] = {}
        all_activations: List[Dict] = []

        for tradition in self._TRADITIONS:
            active_list = []
            for symbol in self._catalogues.get(tradition, []):
                result = self._decode_symbol(symbol, longitudes, tradition)
                if result.get("active"):
                    active_list.append(result)
                    all_activations.append(result)
            per_tradition[tradition] = active_list

        # Detect convergence (multiple civilizations on same aspect)
        convergence = self._detect_convergence(all_activations)

        # ═══════════════════════════════════════════════════════════
        # LAYERED TIMEFRAME SCORING
        # Planet pairs have vastly different speeds. Moon aspects last
        # hours, Mercury days, Venus/Mars weeks, outer planets years.
        # Score each tier separately, then combine with cross-tier
        # agreement weighting. No more additive bonus stacking.
        # ═══════════════════════════════════════════════════════════
        if all_activations:
            # Count biases (used for details + phase)
            buy_count = sum(1 for a in all_activations if a["trading_bias"] == "BUY")
            sell_count = sum(1 for a in all_activations if a["trading_bias"] == "SELL")
            hold_count = sum(1 for a in all_activations if a["trading_bias"] == "HOLD")

            # ── Classify activations into speed tiers ──
            tier_activations: Dict[str, List[Dict]] = {}
            for a in all_activations:
                tier = self._get_pair_speed_tier(a["planet_pair"])
                tier_activations.setdefault(tier, []).append(a)

            # ── Compute per-tier scores ──
            tier_scores: Dict[str, Dict] = {}
            for tier_name, tier_acts in tier_activations.items():
                t_weight = sum(a["activation_strength"] for a in tier_acts)
                if t_weight > 0:
                    t_score = sum(
                        a["signal_strength"] * a["activation_strength"]
                        for a in tier_acts
                    ) / t_weight
                else:
                    t_score = 0.5

                t_buy = sum(1 for a in tier_acts if a["trading_bias"] == "BUY")
                t_sell = sum(1 for a in tier_acts if a["trading_bias"] == "SELL")
                t_hold = sum(1 for a in tier_acts if a["trading_bias"] == "HOLD")

                if t_buy > t_sell:
                    t_direction = "BUY"
                elif t_sell > t_buy:
                    t_direction = "SELL"
                else:
                    t_direction = "HOLD"

                # Small bias shift within tier (capped to prevent inflation)
                bias_shift = (t_buy - t_sell) * 0.01
                t_score = max(0.0, min(1.0, t_score + bias_shift))

                tier_label = self._SPEED_TIERS.get(tier_name, {}).get("label", "?")
                tier_scores[tier_name] = {
                    "score": round(t_score, 4),
                    "direction": t_direction,
                    "label": tier_label,
                    "buy": t_buy,
                    "sell": t_sell,
                    "hold": t_hold,
                    "count": len(tier_acts),
                    "symbols": [a["rune_name"] for a in tier_acts],
                }

            # ── Weighted combination of tier scores ──
            total_tier_weight = 0.0
            weighted_score_sum = 0.0
            for tier_name, t_data in tier_scores.items():
                tw = self._SPEED_TIERS.get(tier_name, {}).get("weight", 0.10)
                weighted_score_sum += t_data["score"] * tw
                total_tier_weight += tw

            if total_tier_weight > 0:
                score = weighted_score_sum / total_tier_weight
            else:
                score = 0.5

            # ── Cross-tier agreement factor ──
            # All tiers agree → confident score. Disagreement → pull toward 0.5.
            tier_directions = [
                t["direction"] for t in tier_scores.values()
                if t["direction"] != "HOLD"
            ]
            if tier_directions:
                dominant_dir = max(set(tier_directions), key=tier_directions.count)
                agreement_ratio = tier_directions.count(dominant_dir) / len(tier_directions)
                # Disagreement pulls score toward 0.5 (uncertainty)
                disagreement = 1.0 - agreement_ratio
                score = score * (1.0 - disagreement * 0.4) + 0.5 * (disagreement * 0.4)
            else:
                agreement_ratio = 0.0
                score = 0.5  # All HOLD = pure uncertainty

            # ── Combination Intelligence as MULTIPLIERS (not additive) ──
            # Bridge bonus: multiplicative, capped at 8% boost
            bridge_best = 0.0
            for bridge in convergence.get("bridge_activations", []):
                bridge_best = max(bridge_best, bridge.get("bridge_bonus", 0))
            if bridge_best > 0:
                score *= (1.0 + min(bridge_best, 0.08))

            # Golden Five: confirms direction, max 5% multiplier
            golden = convergence.get("golden_five", {})
            if golden.get("unanimous") and golden.get("consensus_direction"):
                overall_lean = "BUY" if buy_count > sell_count else "SELL"
                if golden["consensus_direction"] == overall_lean:
                    score *= 1.05  # Direction confirmed
                if golden.get("japanese_keystone"):
                    score *= 1.02  # Keystone tradition agrees

            score = max(0.0, min(1.0, score))

        else:
            score = 0.5
            buy_count = sell_count = hold_count = 0
            tier_scores = {}
            tier_directions = []
            agreement_ratio = 0.0

        # Determine phase
        if score >= 0.80:
            phase = "ANCIENT_FIRE"     # All traditions blaze — maximum signal
        elif score >= 0.65:
            phase = "ANCIENT_LIGHT"    # Clear ancient guidance
        elif score >= 0.50:
            phase = "ANCIENT_FLUX"     # Mixed signals across traditions
        elif score >= 0.35:
            phase = "ANCIENT_SHADOW"   # Caution symbols dominate
        else:
            phase = "ANCIENT_VOID"     # Destructive patterns across traditions

        # Find the strongest single activation
        dominant = None
        if all_activations:
            dominant = max(all_activations, key=lambda a: a["activation_strength"])

        if dominant:
            trad_icon = self._TRADITIONS.get(dominant["tradition"], {}).get("icon", "?")
            dominant_signal = (
                f"{dominant['rune_unicode']} {dominant['rune_name']} "
                f"({trad_icon} {dominant['tradition']}, "
                f"{dominant['geometry']}, "
                f"{dominant['aspect']} {dominant['separation_deg']}°)"
            )
        else:
            dominant_signal = "The star chart is silent — no ancient geometry active"

        # Build active lists per tradition
        active_summary = {}
        for tradition in self._TRADITIONS:
            icon = self._TRADITIONS[tradition]["icon"]
            active_summary[f"active_{tradition}_count"] = len(per_tradition[tradition])

        # Convergence message
        conv_msg = ""
        if convergence["convergences"]:
            best = max(convergence["convergences"], key=lambda c: c["tradition_count"])
            conv_msg = (
                f"CONVERGENCE: {best['tradition_count']} traditions agree on "
                f"{best['aspect_key']} — {', '.join(best['symbols'])}"
            )

        total_symbols = sum(len(self._catalogues.get(k, [])) for k in self._TRADITIONS)

        details = {
            **active_summary,
            "total_active": len(all_activations),
            "total_symbols": total_symbols,
            "buy_symbols": buy_count,
            "sell_symbols": sell_count,
            "hold_symbols": hold_count,
            "dominant_name": dominant["rune_name"] if dominant else "None",
            "dominant_unicode": dominant["rune_unicode"] if dominant else "",
            "dominant_tradition": dominant["tradition"] if dominant else "none",
            "dominant_geometry": dominant["geometry"] if dominant else "NONE",
            "convergence_count": convergence["convergence_count"],
            "max_convergence_traditions": convergence["max_traditions"],
            "convergence_message": conv_msg,
            "convergences": convergence["convergences"],
            "timeframe_layers": tier_scores,
            # Combination Intelligence fields
            "bridge_count": convergence.get("bridge_count", 0),
            "bridge_activations": convergence.get("bridge_activations", []),
            "best_bridge_accuracy": convergence.get("best_bridge_accuracy", 0.0),
            "golden_five": convergence.get("golden_five", {}),
            "active_symbols": [
                f"{a['rune_unicode']}{a['rune_name']}[{a['tradition']}]"
                f"({a['aspect']},{a['separation_deg']}°,{a['trading_bias']})"
                for a in sorted(all_activations, key=lambda x: -x["activation_strength"])
            ],
            "planetary_longitudes": {p: round(l, 2) for p, l in longitudes.items()},
        }

        # Build convergence + bridge message
        bridge_msgs = []
        for b in convergence.get("bridge_activations", []):
            bridge_msgs.append(
                f"BRIDGE {b['aspect_key']} ({b['bridge_accuracy']:.0%} accuracy) — "
                f"{', '.join(b['traditions'])}"
            )
        if bridge_msgs:
            details["bridge_message"] = " | ".join(bridge_msgs)

        golden = convergence.get("golden_five", {})
        if golden.get("unanimous"):
            g5_trads = ", ".join(sorted(golden.get("traditions_voting", {}).keys()))
            g5_dir = golden.get("consensus_direction", "?")
            details["golden_five_message"] = (
                f"GOLDEN FIVE CONSENSUS: {g5_dir} "
                f"({golden['active_count']}/5 agree) — {g5_trads}"
            )

        # Confidence: based on tier coverage, cross-tier agreement,
        # and convergence — no more jumping to 0.97 on any bridge.
        if all_activations:
            active_tier_count = len(tier_scores)
            # Base: more tiers covered = more complete picture
            _conf = 0.40 + min(0.30, active_tier_count * 0.06)
            # Cross-tier agreement boosts confidence
            if tier_directions:
                _conf += agreement_ratio * 0.15
            # Convergence adds modest boost (not 0.15 anymore!)
            if convergence.get("bridge_count", 0) > 0:
                _conf = min(0.92, _conf + 0.08)
            elif golden.get("unanimous"):
                _conf = min(0.90, _conf + 0.06)
            elif convergence["max_traditions"] >= 3:
                _conf = min(0.88, _conf + 0.04)
            elif convergence["max_traditions"] >= 2:
                _conf = min(0.85, _conf + 0.02)
        else:
            _conf = 0.3

        return OracleReading(
            oracle="RUNES",
            timestamp=time.time(),
            score=max(0.0, min(1.0, score)),
            phase=phase,
            dominant_signal=dominant_signal,
            details=details,
            confidence=_conf,
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF SENTIMENT - Fear/Greed + Yahoo Finance News + Geopolitics
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfSentiment:
    """
    The 7th Oracle: SENTIMENT.
    Reads the emotional pulse of the global market through:
      1. Crypto Fear & Greed Index (via Lyra's FearGreedFetcher)
      2. Yahoo Finance RSS news headlines (geopolitics, macro events)
      3. King's Order Flow Velocity (buy/sell speed + participant intent)
      4. Lyra's emotional resonance (if available)

    This Oracle gives the Seer FEELING — not just seeing.
    """

    # Bearish / Bullish keyword dictionaries for Yahoo headline sentiment
    BEARISH_KEYWORDS = [
        "crash", "collapse", "recession", "war", "sanctions", "tariff",
        "default", "bankruptcy", "layoff", "downgrade", "plunge", "fear",
        "panic", "sell-off", "selloff", "inflation", "hawkish", "tighten",
        "geopolitical", "conflict", "escalat", "crisis", "bear market",
        "downturn", "slump", "threat", "hack", "breach", "fraud",
        "investigation", "lawsuit", "ban", "restrict", "shutdown",
    ]
    BULLISH_KEYWORDS = [
        "rally", "surge", "boom", "bull", "record high", "all-time high",
        "ath", "breakout", "adoption", "approval", "etf approved",
        "institutional", "accumulation", "dovish", "rate cut",
        "stimulus", "growth", "partnership", "upgrade", "breakthrough",
        "recovery", "rebound", "milestone", "launch", "expansion",
        "inflow", "bullish", "optimism", "innovation",
    ]

    YAHOO_RSS_URL = "https://finance.yahoo.com/news/rssindex"
    YAHOO_CRYPTO_RSS_URL = "https://finance.yahoo.com/rss/topfinstories"

    def __init__(self):
        self._fg_fetcher = None
        self._news_cache: Dict[str, Any] = {}
        self._news_cache_time: float = 0
        self._NEWS_CACHE_TTL = 600  # 10 minutes

    def _get_fg_fetcher(self):
        """Lazy-load the FearGreedFetcher from Lyra."""
        if self._fg_fetcher is None:
            try:
                from aureon.trading.aureon_lyra import get_fear_greed_fetcher
                self._fg_fetcher = get_fear_greed_fetcher()
            except ImportError:
                pass
        return self._fg_fetcher

    def read(self, market_data: Dict[str, Any] = None) -> OracleReading:
        """Read the sentiment oracle — aggregates Fear/Greed + News + Macro + Velocity."""
        scores = []
        details = {}

        # ── 1. FEAR & GREED INDEX ──
        fg_score, fg_details = self._read_fear_greed()
        scores.append(("fear_greed", fg_score, 0.25))
        details.update(fg_details)

        # ── 2. YAHOO FINANCE NEWS / GEOPOLITICS ──
        news_score, news_details = self._read_yahoo_news()
        scores.append(("news_sentiment", news_score, 0.18))
        details.update(news_details)

        # ── 3. GLOBAL MACRO LANDSCAPE ──
        macro_score, macro_details = self._read_macro_landscape()
        scores.append(("macro_landscape", macro_score, 0.30))
        details.update(macro_details)

        # ── 4. KING'S ORDER FLOW VELOCITY ──
        flow_score, flow_details = self._read_order_flow()
        scores.append(("order_flow", flow_score, 0.18))
        details.update(flow_details)

        # ── 5. LYRA RESONANCE (if available) ──
        lyra_score, lyra_details = self._read_lyra_resonance()
        scores.append(("lyra_resonance", lyra_score, 0.09))
        details.update(lyra_details)

        # Weighted combination — skip oracles whose live source returned None
        # (Stage AP) and reweight the remaining components proportionally so a
        # fake neutral 0.5 isn't folded into the unified sentiment.
        active = [(name, s, w) for name, s, w in scores if s is not None]
        skipped = [name for name, s, _ in scores if s is None]
        total_weight = sum(w for _, _, w in active)
        if active and total_weight > 0:
            unified = sum(s * w for _, s, w in active) / total_weight
            unified = max(0.0, min(1.0, unified))
            details["sentiment_oracles_active"] = [n for n, _, _ in active]
            if skipped:
                details["sentiment_oracles_skipped"] = skipped
                logger.warning("[insufficient-data] sentiment unified score "
                               "computed from %d/%d active oracles (skipped: %s)",
                               len(active), len(scores), skipped)
        else:
            # Every oracle returned None — there is no real sentiment signal.
            # Mark the unified score as neutral 0.5 with an explicit "no sources
            # active" detail so callers can detect.
            unified = 0.5
            details["sentiment_oracles_active"] = []
            details["sentiment_oracles_skipped"] = skipped
            details["sentiment_no_sources_active"] = True
            logger.warning("[insufficient-data] sentiment: ALL %d oracles "
                           "returned None; unified=0.5 with sentiment_no_sources_active=True",
                           len(scores))

        # Phase determination
        if unified >= 0.75:
            phase = "EUPHORIA"
            dominant = f"Market euphoria — sentiment {unified:.0%} bullish"
        elif unified >= 0.60:
            phase = "OPTIMISM"
            dominant = f"Market optimism — sentiment {unified:.0%} positive"
        elif unified >= 0.45:
            phase = "NEUTRAL"
            dominant = f"Market neutral — sentiment balanced at {unified:.0%}"
        elif unified >= 0.30:
            phase = "ANXIETY"
            dominant = f"Market anxiety — sentiment {1-unified:.0%} fearful"
        else:
            phase = "PANIC"
            dominant = f"Market PANIC — sentiment {1-unified:.0%} extreme fear"

        details["component_scores"] = {name: round(s, 4) for name, s, _ in scores}

        # Confidence:  higher if we have real data sources
        sources_active = sum(1 for name, _, _ in scores
                             if details.get(f"{name}_source_active", True))
        confidence = 0.3 + sources_active * 0.15

        return OracleReading(
            oracle="SENTIMENT",
            timestamp=time.time(),
            score=unified,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=min(0.95, confidence),
        )

    def _read_fear_greed(self) -> Tuple[Optional[float], Dict]:
        """Read Fear & Greed Index.

        Returns (score, details). ``score`` is ``None`` when the live FG
        source is unavailable so the aggregator can drop this component
        and reweight the remainder, rather than fold a synthetic 0.5
        into the unified sentiment reading.
        """
        details = {}
        fetcher = self._get_fg_fetcher()
        if fetcher:
            try:
                fg = fetcher.fetch()
                index_val = fg.get("fear_greed_index", 50)
                details["fg_index"] = index_val
                details["fg_label"] = fg.get("fear_greed_label", "Neutral")
                details["fg_source"] = fg.get("source", "default")
                details["fg_momentum"] = fg.get("market_momentum", 0.0)
                details["fg_btc_24h"] = fg.get("btc_24h_change", 0.0)
                details["fg_gainers_ratio"] = fg.get("top_gainers_ratio", 0.5)
                # Map 0-100 index to 0-1 score
                score = index_val / 100.0
                return score, details
            except Exception as e:
                logger.warning(f"[insufficient-data] _read_fear_greed source error: {e}")
        details["fear_greed_source_active"] = False
        logger.warning("[insufficient-data] _read_fear_greed: no live source; "
                       "returning None so aggregator reweights without this component")
        return None, details

    def _read_yahoo_news(self) -> Tuple[Optional[float], Dict]:
        """
        Read Yahoo Finance RSS headlines and analyze for geopolitical/market sentiment.
        Uses keyword matching on headlines to gauge bullish vs bearish tone.
        """
        details = {}
        now = time.time()

        # Check cache
        if self._news_cache and (now - self._news_cache_time) < self._NEWS_CACHE_TTL:
            return self._news_cache.get("score", 0.5), self._news_cache.get("details", {})

        headlines = []
        try:
            import urllib.request
            for url in [self.YAHOO_RSS_URL, self.YAHOO_CRYPTO_RSS_URL]:
                try:
                    req = urllib.request.Request(url, headers={
                        "User-Agent": "AureonSeer/1.0"
                    })
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        raw = resp.read().decode("utf-8", errors="replace")
                    # Simple XML parsing — extract <title> elements
                    import re
                    titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", raw)
                    if not titles:
                        titles = re.findall(r"<title>(.*?)</title>", raw)
                    headlines.extend(titles)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"OracleOfSentiment Yahoo news error: {e}")

        if not headlines:
            details["news_source_active"] = False
            details["news_headlines_count"] = 0
            logger.warning("[insufficient-data] _read_yahoo_news: no headlines "
                           "fetched; returning None so aggregator reweights")
            return None, details

        # Analyze headlines
        bullish_count = 0
        bearish_count = 0
        total = len(headlines)
        keyword_hits = []

        for h in headlines:
            h_lower = h.lower()
            is_bull = any(kw in h_lower for kw in self.BULLISH_KEYWORDS)
            is_bear = any(kw in h_lower for kw in self.BEARISH_KEYWORDS)
            if is_bull and not is_bear:
                bullish_count += 1
            elif is_bear and not is_bull:
                bearish_count += 1
                keyword_hits.append(h[:80])

        neutral_count = total - bullish_count - bearish_count
        if total > 0:
            # Score: 0 = all bearish, 0.5 = neutral, 1 = all bullish
            score = (bullish_count * 1.0 + neutral_count * 0.5) / total
        else:
            score = 0.5

        details["news_headlines_count"] = total
        details["news_bullish"] = bullish_count
        details["news_bearish"] = bearish_count
        details["news_neutral"] = neutral_count
        details["news_score"] = round(score, 4)
        details["news_bearish_headlines"] = keyword_hits[:5]  # Top 5 bearish headlines
        details["news_source_active"] = True

        # Cache
        self._news_cache = {"score": score, "details": details}
        self._news_cache_time = now

        return score, details

    def _read_order_flow(self) -> Tuple[Optional[float], Dict]:
        """Read the King's Order Flow Velocity.

        Returns ``(None, details)`` when king_accounting is unavailable so
        the aggregator drops this component instead of folding a fake 0.5
        into the unified sentiment.
        """
        details = {}
        try:
            from aureon.bots.king_accounting import get_order_flow_velocity
            ofv = get_order_flow_velocity()
            report = ofv.get_velocity_report()
            details["flow_pressure"] = report.get("pressure_ratio", 0.5)
            details["flow_momentum"] = report.get("flow_momentum", 0.5)
            details["flow_velocity"] = report.get("total_velocity", 0)
            details["flow_intent"] = report.get("intent", "QUIET")
            details["flow_surge"] = report.get("surge_detected", False)
            details["flow_acceleration"] = report.get("acceleration", 0.0)
            # Map pressure_ratio directly to score (0 = all sells, 1 = all buys)
            score = report.get("flow_momentum", None)
            if score is not None:
                return float(score), details
        except Exception as e:
            logger.warning(f"[insufficient-data] _read_order_flow source error: {e}")
        details["order_flow_source_active"] = False
        logger.warning("[insufficient-data] _read_order_flow: no live source; "
                       "returning None so aggregator reweights without this component")
        return None, details

    def _read_lyra_resonance(self) -> Tuple[Optional[float], Dict]:
        """Read Lyra's latest emotional resonance.

        Returns ``(None, details)`` when Lyra hasn't produced a resonance
        reading yet so the aggregator reweights other oracles rather than
        absorbing a fake neutral 0.5.
        """
        details = {}
        try:
            from aureon.trading.aureon_lyra import get_lyra
            lyra = get_lyra()
            if lyra.latest_resonance:
                r = lyra.latest_resonance
                details["lyra_score"] = r.unified_score
                details["lyra_grade"] = r.grade
                details["lyra_zone"] = r.emotional_zone
                details["lyra_freq"] = r.emotional_frequency
                details["lyra_action"] = r.action
                return r.unified_score, details
        except Exception as e:
            logger.warning(f"[insufficient-data] _read_lyra_resonance source error: {e}")
        details["lyra_resonance_source_active"] = False
        return None, details

    # ── MACRO LANDSCAPE — full global view ──────────────────────────────

    _MACRO_CACHE: Dict[str, Any] = {}
    _MACRO_CACHE_TIME: float = 0.0
    _MACRO_CACHE_TTL: float = 300.0  # 5 minutes

    def _read_macro_landscape(self) -> Tuple[Optional[float], Dict]:
        """
        Reads the full global macro landscape from open-source APIs.
        Sources (all free, no API key required):
          • Yahoo Finance chart API  → S&P 500, NASDAQ, DXY, Gold, Oil, 10yr yield
          • CoinGecko /global        → crypto market cap 24h change, BTC dominance
          • CoinGecko /coins/markets → altcoin breadth (gainers vs losers in top 100)
          • Alternative.me           → already in fear/greed, used for reference

        Signal logic (crypto-centric):
          BULLISH signals  → risk-on assets rising (SPX↑ NASDAQ↑ crypto-cap↑)
          BEARISH signals  → risk-off flows (DXY↑ Gold↑ Yields rising fast)
        """
        import time as _time
        now = _time.time()
        if OracleOfSentiment._MACRO_CACHE and (now - OracleOfSentiment._MACRO_CACHE_TIME) < OracleOfSentiment._MACRO_CACHE_TTL:
            return OracleOfSentiment._MACRO_CACHE.get("score", 0.5), OracleOfSentiment._MACRO_CACHE.get("details", {})

        details: Dict[str, Any] = {"macro_source_active": False}
        signals: List[Tuple[str, float, float]] = []  # (name, score 0-1, weight)

        try:
            import requests as _req

            # ── 1. Yahoo Finance: S&P 500and NASDAQ (risk-on gauge) ──
            for ticker, label, weight in [
                ("^GSPC",    "sp500",   0.18),
                ("^IXIC",    "nasdaq",  0.15),
            ]:
                try:
                    r = _req.get(
                        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                        params={"interval": "1d", "range": "2d"},
                        headers={"User-Agent": "AureonSeer/2.0"},
                        timeout=6,
                    )
                    data = r.json()
                    closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                    closes = [c for c in closes if c is not None]
                    if len(closes) >= 2:
                        chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                        # Map: -3% → 0.0, 0% → 0.5, +3% → 1.0 (clamped)
                        score = max(0.0, min(1.0, 0.5 + chg_pct / 6.0))
                        signals.append((label, score, weight))
                        details[f"macro_{label}_chg"] = round(chg_pct, 3)
                        details[f"macro_{label}_score"] = round(score, 3)
                except Exception:
                    pass

            # ── 2. Yahoo Finance: DXY (strong dollar = bearish crypto) ──
            try:
                r = _req.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB",
                    params={"interval": "1d", "range": "2d"},
                    headers={"User-Agent": "AureonSeer/2.0"},
                    timeout=6,
                )
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in closes if c is not None]
                if len(closes) >= 2:
                    chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                    # INVERSE: DXY up = bearish for crypto
                    score = max(0.0, min(1.0, 0.5 - chg_pct / 4.0))
                    signals.append(("dxy", score, 0.20))
                    details["macro_dxy_chg"] = round(chg_pct, 3)
                    details["macro_dxy_score"] = round(score, 3)
                    details["macro_dxy_signal"] = "bearish_crypto" if chg_pct > 0.3 else ("bullish_crypto" if chg_pct < -0.3 else "neutral")
            except Exception:
                pass

            # ── 3. Yahoo Finance: Gold (risk-off safe haven) ──
            try:
                r = _req.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
                    params={"interval": "1d", "range": "2d"},
                    headers={"User-Agent": "AureonSeer/2.0"},
                    timeout=6,
                )
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in closes if c is not None]
                if len(closes) >= 2:
                    chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                    # Gold surging = risk-off flight → mild bearish for crypto
                    score = max(0.0, min(1.0, 0.5 - chg_pct / 5.0))
                    signals.append(("gold", score, 0.08))
                    details["macro_gold_chg"] = round(chg_pct, 3)
                    details["macro_gold_score"] = round(score, 3)
            except Exception:
                pass

            # ── 4. Yahoo Finance: 10-Year Treasury Yield ──
            try:
                r = _req.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/^TNX",
                    params={"interval": "1d", "range": "5d"},
                    headers={"User-Agent": "AureonSeer/2.0"},
                    timeout=6,
                )
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in closes if c is not None]
                if len(closes) >= 2:
                    chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                    # Rising yields = tighter conditions = bearish risk assets
                    score = max(0.0, min(1.0, 0.5 - chg_pct / 6.0))
                    signals.append(("bonds_10yr", score, 0.12))
                    details["macro_10yr_yield"] = round(closes[-1], 3)
                    details["macro_10yr_chg"] = round(chg_pct, 3)
                    details["macro_10yr_score"] = round(score, 3)
            except Exception:
                pass

            # ── 5. Yahoo Finance: Crude Oil (WTI) ──
            try:
                r = _req.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/CL=F",
                    params={"interval": "1d", "range": "2d"},
                    headers={"User-Agent": "AureonSeer/2.0"},
                    timeout=6,
                )
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in closes if c is not None]
                if len(closes) >= 2:
                    chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                    # Moderate oil rise = growth signal (mildly bullish), spike = inflationary (bearish)
                    score = max(0.0, min(1.0, 0.5 + chg_pct / 8.0)) if abs(chg_pct) < 3 else max(0.0, min(1.0, 0.5 - chg_pct / 10.0))
                    signals.append(("oil", score, 0.05))
                    details["macro_oil_chg"] = round(chg_pct, 3)
            except Exception:
                pass

            # ── 6. CoinGecko: Global crypto market cap + BTC dominance ──
            try:
                r = _req.get(
                    "https://api.coingecko.com/api/v3/global",
                    timeout=8,
                )
                gdata = r.json().get("data", {})
                cap_chg = gdata.get("market_cap_change_percentage_24h_usd", 0.0)
                btc_dom = gdata.get("market_cap_percentage", {}).get("btc", 50.0)

                # Crypto market cap 24h change
                cap_score = max(0.0, min(1.0, 0.5 + cap_chg / 10.0))
                signals.append(("crypto_cap", cap_score, 0.18))
                details["macro_crypto_cap_chg"] = round(cap_chg, 3)
                details["macro_crypto_cap_score"] = round(cap_score, 3)
                details["macro_btc_dominance"] = round(btc_dom, 1)

                # BTC dominance rising = altcoins bleeding (bearish for alts)
                # Neutral signal — just informational
                details["macro_btc_dom_signal"] = "alts_bleeding" if btc_dom > 55 else ("balanced" if btc_dom > 45 else "alts_leading")
            except Exception:
                pass

            # ── 7. CoinGecko: Top-100 altcoin breadth (gainers vs losers) ──
            try:
                r = _req.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": 100,
                        "page": 1,
                        "price_change_percentage": "24h",
                    },
                    timeout=10,
                )
                coins = r.json()
                gainers = sum(1 for c in coins if (c.get("price_change_percentage_24h") or 0) > 0)
                losers = len(coins) - gainers
                breadth = gainers / len(coins) if coins else 0.5
                signals.append(("altcoin_breadth", breadth, 0.04))
                details["macro_altcoin_gainers"] = gainers
                details["macro_altcoin_losers"] = losers
                details["macro_altcoin_breadth"] = round(breadth, 3)
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"OracleOfSentiment macro error: {e}")

        if not signals:
            details["macro_source_active"] = False
            logger.warning("[insufficient-data] _read_macro_landscape: no signals "
                           "gathered (Yahoo / CoinGecko / DXY all failed); returning "
                           "None so aggregator reweights without this component")
            return None, details

        total_w = sum(w for _, _, w in signals)
        macro_score = sum(s * w for _, s, w in signals) / total_w if total_w > 0 else 0.5
        macro_score = max(0.0, min(1.0, macro_score))

        details["macro_source_active"] = True
        details["macro_unified_score"] = round(macro_score, 4)
        details["macro_signals_count"] = len(signals)
        details["macro_component_scores"] = {n: round(s, 3) for n, s, _ in signals}

        # Human-readable macro summary
        if macro_score >= 0.65:
            details["macro_summary"] = "RISK-ON: Global macro favours crypto entry"
        elif macro_score >= 0.52:
            details["macro_summary"] = "MILD RISK-ON: Macro broadly supportive"
        elif macro_score >= 0.48:
            details["macro_summary"] = "NEUTRAL: Macro mixed signals"
        elif macro_score >= 0.35:
            details["macro_summary"] = "MILD RISK-OFF: Dollar/yields pressuring crypto"
        else:
            details["macro_summary"] = "RISK-OFF: Global macro headwinds for crypto"

        OracleOfSentiment._MACRO_CACHE = {"score": macro_score, "details": details}
        OracleOfSentiment._MACRO_CACHE_TIME = now
        return macro_score, details


# ═══════════════════════════════════════════════════════════════════════════
# WAR COUNSEL - The Seer Consults the Warriors
# ═══════════════════════════════════════════════════════════════════════════

class WarCounsel:
    """
    The Seer takes counsel from the War Systems:
      - IRA Sniper Mode: Zero-loss discipline, entry validation
      - Guerrilla Warfare Engine: Tactical mode, ambush readiness
      - War Strategy: Quick kill analysis, battlefront assessment

    The War Counsel does NOT override the Seer — it provides
    TACTICAL INTELLIGENCE that modifies the Seer's risk assessment.
    """

    def __init__(self):
        self._sniper = None
        self._guerrilla = None
        self._war_strategy = None

    def _load(self):
        """Lazy-load war systems."""
        if self._sniper is None:
            try:
                from aureon.scanners.ira_sniper_mode import get_sniper_config
                self._sniper = get_sniper_config()
            except ImportError:
                pass
        if self._guerrilla is None:
            try:
                from aureon.wisdom.guerrilla_warfare_engine import GUERRILLA_CONFIG
                self._guerrilla = GUERRILLA_CONFIG
            except ImportError:
                pass
        if self._war_strategy is None:
            try:
                from aureon.command_centers.war_strategy import WarStrategy
                self._war_strategy = WarStrategy()
            except (ImportError, Exception):
                pass

    def get_counsel(self, unified_score: float = 0.5,
                    sentiment_data: Dict = None) -> Dict[str, Any]:
        """
        Get war counsel to modify the Seer's assessment.
        Returns tactical adjustments:
          - risk_modifier: float (0.5 to 1.5)
          - tactical_mode: str
          - war_says: str (advisory message)
          - entry_discipline: bool (strict or relaxed)
        """
        self._load()
        counsel = {
            "risk_modifier": 1.0,
            "tactical_mode": "STANDARD",
            "war_says": "No war counsel available.",
            "entry_discipline": True,
            "sources_active": 0,
        }

        messages = []
        risk_mods = []
        sources = 0

        # ── IRA SNIPER COUNSEL ──
        if self._sniper:
            sources += 1
            zero_loss = self._sniper.get("ZERO_LOSS_MODE", True)
            min_threshold = self._sniper.get("MIN_SCORE_THRESHOLD", 0.60)
            fear_off = self._sniper.get("FEAR_MODE", False) is False

            if zero_loss:
                counsel["entry_discipline"] = True
                messages.append("IRA: ZERO LOSS MODE active. Every kill must profit.")

            if unified_score < min_threshold:
                risk_mods.append(0.6)
                messages.append(f"IRA: Score {unified_score:.2f} below sniper threshold {min_threshold}. Reduce exposure.")
            else:
                risk_mods.append(1.0)
                messages.append(f"IRA: Score {unified_score:.2f} approved. Take the shot.")

        # ── GUERRILLA WARFARE COUNSEL ──
        if self._guerrilla:
            sources += 1
            preemptive = self._guerrilla.get("PREEMPTIVE_EXIT_ENABLED", True)
            min_ambush = self._guerrilla.get("MIN_AMBUSH_SCORE", 0.65)
            coord_threshold = self._guerrilla.get("COORDINATED_STRIKE_THRESHOLD", 0.80)

            if unified_score >= coord_threshold:
                counsel["tactical_mode"] = "COORDINATED_STRIKE"
                risk_mods.append(1.3)
                messages.append("GUERRILLA: COORDINATED STRIKE conditions met! Multi-front attack.")
            elif unified_score >= min_ambush:
                counsel["tactical_mode"] = "AMBUSH"
                risk_mods.append(1.1)
                messages.append("GUERRILLA: Ambush conditions favorable. Patient engagement.")
            elif unified_score >= 0.50:
                counsel["tactical_mode"] = "FLYING_COLUMN"
                risk_mods.append(0.9)
                messages.append("GUERRILLA: Flying column mode. Quick in, quick out.")
            else:
                counsel["tactical_mode"] = "RETREAT"
                risk_mods.append(0.5)
                messages.append("GUERRILLA: RETREAT! Market hostile. Live to fight another day.")

            if preemptive:
                messages.append("GUERRILLA: Preemptive exit ENABLED — will exit before reversal.")

        # ── WAR STRATEGY QUICK KILL ──
        if self._war_strategy:
            sources += 1
            try:
                if hasattr(self._war_strategy, "get_strategy_assessment"):
                    assessment = self._war_strategy.get_strategy_assessment()
                    if assessment:
                        strat_score = assessment.get("score", 0.5) if isinstance(assessment, dict) else 0.5
                        risk_mods.append(0.7 + strat_score * 0.6)
                        messages.append(f"WAR STRATEGY: Assessment score {strat_score:.2f}")
                elif hasattr(self._war_strategy, "quick_kill_analysis"):
                    qk = self._war_strategy.quick_kill_analysis()
                    if qk:
                        messages.append(f"WAR STRATEGY: Quick kill probability assessed.")
            except Exception as e:
                logger.debug(f"WarCounsel strategy error: {e}")

        # Geopolitical tension modifier from news sentiment
        if sentiment_data:
            news_bearish = sentiment_data.get("news_bearish", 0)
            news_total = sentiment_data.get("news_headlines_count", 1)
            if news_total > 0:
                bearish_ratio = news_bearish / news_total
                if bearish_ratio > 0.5:
                    risk_mods.append(0.7)
                    messages.append(f"GEOPOLITICS: {bearish_ratio:.0%} bearish headlines. Caution advised.")
                elif bearish_ratio > 0.3:
                    risk_mods.append(0.85)
                    messages.append(f"GEOPOLITICS: Elevated bearish news ({bearish_ratio:.0%}). Monitor closely.")

        # Final risk modifier
        if risk_mods:
            counsel["risk_modifier"] = round(sum(risk_mods) / len(risk_mods), 3)
        counsel["war_says"] = " | ".join(messages) if messages else "War counsel awaits."
        counsel["sources_active"] = sources

        return counsel


# ═══════════════════════════════════════════════════════════════════════════
# 8th ORACLE: ORACLE OF MARGIN - Leveraged Opportunity Intelligence
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfMargin:
    """
    Oracle of Margin - Reads Kraken margin account health, available
    leverage pairs, and market conditions to predict whether leveraged
    positions can generate additional revenue safely.

    Signals:
      - margin_score:  0-1 how favourable conditions are for margin trading
      - leverage_rec:  recommended leverage (2-5x) or 0 if not recommended
      - direction:     'LONG' or 'SHORT' or 'NONE'
      - conviction:    0-1 how strongly the oracle believes in the direction
      - eligible_pairs: list of pairs currently supporting margin
    """

    def __init__(self):
        self._kraken = None
        self._last_margin_pairs: dict = {}
        self._last_trade_balance: dict = {}
        self._last_fetch_ts: float = 0
        self._cache_ttl: float = 120  # refresh margin data every 2 min

    def _load_kraken(self):
        if self._kraken is None:
            try:
                from aureon.exchanges.kraken_client import KrakenClient
                self._kraken = KrakenClient()
            except ImportError:
                pass

    def _refresh_margin_data(self):
        """Refresh margin account & pair data (rate-limit aware)."""
        if time.time() - self._last_fetch_ts < self._cache_ttl:
            return
        self._load_kraken()
        if not self._kraken:
            return
        try:
            self._last_trade_balance = self._kraken.get_trade_balance() or {}
        except Exception as e:
            logger.debug(f"OracleOfMargin: trade_balance error: {e}")
        try:
            self._last_margin_pairs = self._kraken.get_margin_pairs() or {}
        except Exception as e:
            logger.debug(f"OracleOfMargin: margin_pairs error: {e}")
        self._last_fetch_ts = time.time()

    def read(self, market_data: dict = None, vision_score: float = 0.5,
             trend: str = "STABLE") -> OracleReading:
        """
        Take a margin reading.

        Uses:
          - Kraken trade balance (equity, free_margin, margin_level)
          - Number of margin-eligible pairs (opportunity breadth)
          - Seer's unified vision score (cosmic alignment for leverage)
          - Market trend direction (IMPROVING / DECLINING / STABLE)
        """
        self._refresh_margin_data()

        score = 0.0
        phase = "MARGIN_OFFLINE"
        dominant = "none"
        details = {}
        conviction = 0.0
        direction = "NONE"
        leverage_rec = 0

        tb = self._last_trade_balance
        mp = self._last_margin_pairs

        if not tb:
            # No margin data — return neutral
            return OracleReading(
                oracle="MARGIN",
                timestamp=time.time(),
                score=0.3,
                phase="MARGIN_OFFLINE",
                dominant_signal="no_margin_data",
                details={"reason": "Kraken margin data unavailable"},
                confidence=0.2,
            )

        # ── Account health scoring ──
        equity = float(tb.get('equity_value', 0) or 0)
        free_margin = float(tb.get('free_margin', 0) or 0)
        margin_used = float(tb.get('margin_amount', 0) or 0)
        margin_level = float(tb.get('margin_level', 0) or 0)
        unrealized = float(tb.get('unrealized_pnl', 0) or 0)

        details['equity'] = equity
        details['free_margin'] = free_margin
        details['margin_used'] = margin_used
        details['margin_level'] = margin_level
        details['unrealized_pnl'] = unrealized

        if equity <= 0:
            return OracleReading(
                oracle="MARGIN", timestamp=time.time(), score=0.1,
                phase="NO_EQUITY", dominant_signal="zero_equity",
                details=details, confidence=0.1,
            )

        # Free margin ratio (higher = safer to trade margin)
        free_ratio = free_margin / equity if equity > 0 else 0
        details['free_margin_ratio'] = round(free_ratio, 4)

        # Exposure ratio (lower = more room)
        exposure_ratio = margin_used / equity if equity > 0 else 1.0
        details['exposure_ratio'] = round(exposure_ratio, 4)

        # Health score: well-funded, low exposure, healthy margin level
        health_score = 0.0
        if free_ratio >= 0.80:
            health_score = 1.0
        elif free_ratio >= 0.50:
            health_score = 0.75
        elif free_ratio >= 0.20:
            health_score = 0.5
        else:
            health_score = 0.2

        # Margin level bonus (>200% = very healthy, <120% = danger)
        if margin_level > 0:
            if margin_level >= 300:
                health_score = min(1.0, health_score + 0.1)
            elif margin_level < 150:
                health_score *= 0.5
            elif margin_level < 120:
                health_score *= 0.2

        # ── Opportunity breadth: how many pairs support margin ──
        n_margin_pairs = len(mp) if isinstance(mp, dict) else 0
        details['margin_eligible_pairs'] = n_margin_pairs
        breadth_score = min(1.0, n_margin_pairs / 50.0)  # 50+ pairs = full score

        # ── Cosmic alignment: is Seer confident enough for leverage? ──
        # High vision = leverage is cosmically supported
        cosmic_score = vision_score

        # ── Trend direction → directional conviction ──
        if trend == "IMPROVING" and vision_score >= 0.65:
            direction = "LONG"
            conviction = min(1.0, vision_score * 1.2)
        elif trend == "DECLINING" and vision_score >= 0.55:
            direction = "SHORT"
            conviction = min(1.0, (1.0 - vision_score) * 1.5)
        else:
            direction = "NONE"
            conviction = 0.0

        # ── Leverage recommendation ──
        # Only recommend leverage when all conditions are favourable
        if conviction > 0.3 and health_score >= 0.5 and cosmic_score >= 0.55:
            if conviction >= 0.80 and health_score >= 0.75:
                leverage_rec = 5
            elif conviction >= 0.65 and health_score >= 0.60:
                leverage_rec = 3
            elif conviction >= 0.45:
                leverage_rec = 2
            else:
                leverage_rec = 0
        else:
            leverage_rec = 0

        # ── Final margin score (weighted blend) ──
        # Health 40%, Cosmic 30%, Breadth 15%, Conviction 15%
        score = (
            health_score * 0.40 +
            cosmic_score * 0.30 +
            breadth_score * 0.15 +
            conviction * 0.15
        )
        score = max(0.0, min(1.0, score))

        # Determine phase
        if score >= 0.75 and leverage_rec >= 3:
            phase = "MARGIN_PRIME"
            dominant = f"leverage_{leverage_rec}x_{direction.lower()}"
        elif score >= 0.55 and leverage_rec >= 2:
            phase = "MARGIN_READY"
            dominant = f"leverage_{leverage_rec}x_{direction.lower()}"
        elif score >= 0.40:
            phase = "MARGIN_CAUTIOUS"
            dominant = "low_conviction"
        else:
            phase = "MARGIN_AVOID"
            dominant = "conditions_unfavourable"

        details['direction'] = direction
        details['conviction'] = round(conviction, 4)
        details['leverage_rec'] = leverage_rec
        details['health_score'] = round(health_score, 4)
        details['cosmic_score'] = round(cosmic_score, 4)
        details['breadth_score'] = round(breadth_score, 4)

        eligible_pairs = list(mp.keys())[:20] if isinstance(mp, dict) else []
        details['eligible_pairs'] = eligible_pairs

        return OracleReading(
            oracle="MARGIN",
            timestamp=time.time(),
            score=score,
            phase=phase,
            dominant_signal=dominant,
            details=details,
            confidence=min(1.0, score * 0.9 + 0.1),
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORACLE OF MAESHOWE - Runic Transmission Lattice Coherence
# ═══════════════════════════════════════════════════════════════════════════

class OracleOfMaeshowe:
    """
    The 9th Oracle: Maeshowe Transmission Lattice Coherence.

    Reads the lattice coherence Γ of the 12th-century Maeshowe runic
    transmission archive, decoded through the Aureon HNC architecture.

    The Dual-Voice Protocol:
      Caller (Ψ₀)   = Wall Auris node frequency (12th-century anchor)
      Seer   (O(t)) = Rune effective frequency  (present observation)
      Beat          = |Caller - Seer| → master beat → Schumann proximity

    Chamber wall → Auris node mapping:
      NE (solstice terminus) => OWL      528 Hz  Wisdom/Pattern
      NW (treasure pointer)  => DEER     396 Hz  Grace/Stability
      SW (seed bank)         => CARGOSHIP 174 Hz  Persistence
      SE (master carver)     => FALCON   210 Hz  Precision

    Lattice coherence thresholds:
      Γ < 0.35           → DEAD_FIELD  (kill-switch)
      0.35 ≤ Γ < 0.945   → ACTIVE_FIELD (transmission in progress)
      Γ ≥ 0.945          → LIGHTHOUSE  (circuit closed)

    Primary Investigator: Gary Leckey, Aureon Institute, March 2026
    Source: Barnes (1994), Smith et al. (2018), Orkneyinga Saga
    """

    def __init__(self):
        self._oracle = None

    def _load(self):
        if self._oracle is None:
            try:
                from aureon.wisdom.maeshowe_seer_decode import OracleMaeshowe as _OM
                self._oracle = _OM()
            except ImportError:
                pass

    def set_pivot_rune(self, left_twigs: int, right_twigs: int):
        """
        Supply the Nr.15 pivot twig counts to close the lattice circuit.
        left_twigs (1-3) = aett, right_twigs (1-8) = position within aett.
        Requires RTI archive access (Smith et al. 2018, ADS York) or
        direct field inspection (Historic Environment Scotland).
        """
        self._load()
        if self._oracle:
            return self._oracle.set_pivot_rune(left_twigs, right_twigs)
        return None

    def read(self) -> OracleReading:
        """Take a Maeshowe lattice reading and return an OracleReading."""
        self._load()
        if self._oracle:
            try:
                return self._oracle.read()
            except Exception as e:
                logger.debug(f"OracleOfMaeshowe read error: {e}")

        # Fallback: neutral reading when module unavailable
        return OracleReading(
            oracle          = "MAESHOWE",
            timestamp       = time.time(),
            score           = 0.5,
            phase           = "ACTIVE_FIELD",
            dominant_signal = "Maeshowe lattice unavailable — using neutral baseline",
            details         = {"gamma": 0.5, "gamma_status": "ACTIVE_FIELD"},
            confidence      = 0.2,
        )


# ═══════════════════════════════════════════════════════════════════════════
# THE ALL-SEEING EYE - Unified Vision
# ═══════════════════════════════════════════════════════════════════════════

class AllSeeingEye:
    """
    Combines all Oracle readings into a single unified vision.
    Each Oracle's score is weighted and combined. The result is a
    complete picture of reality as the Seer perceives it.

    NOW ENHANCED with OracleOfSentiment (7th Oracle), WarCounsel,
    OracleOfMargin (8th Oracle), and OracleOfMaeshowe (9th Oracle).
    """

    def __init__(self):
        self.war_counsel = WarCounsel()

    def combine(self, gaia: OracleReading, cosmos: OracleReading,
                harmony: OracleReading, spirits: OracleReading,
                timeline: OracleReading,
                runes: OracleReading = None,
                sentiment: OracleReading = None,
                margin: OracleReading = None,
                maeshowe: OracleReading = None) -> SeerVision:
        """Combine all 9 Oracle readings into unified vision, then apply War Counsel."""

        # Weighted combination (weights sum to 1.0)
        w = SEER_CONFIG
        unified = (
            gaia.score * w["WEIGHT_GAIA"] +
            cosmos.score * w["WEIGHT_COSMOS"] +
            harmony.score * w["WEIGHT_HARMONY"] +
            spirits.score * w["WEIGHT_SPIRITS"] +
            timeline.score * w["WEIGHT_TIME"] +
            (runes.score if runes else 0.5) * w["WEIGHT_RUNES"] +
            (sentiment.score if sentiment else 0.5) * w["WEIGHT_SENTIMENT"] +
            (maeshowe.score if maeshowe else 0.5) * w["WEIGHT_MAESHOWE"]
        )

        # Confidence-weighted adjustment
        total_confidence = (
            gaia.confidence * w["WEIGHT_GAIA"] +
            cosmos.confidence * w["WEIGHT_COSMOS"] +
            harmony.confidence * w["WEIGHT_HARMONY"] +
            spirits.confidence * w["WEIGHT_SPIRITS"] +
            timeline.confidence * w["WEIGHT_TIME"] +
            (runes.confidence if runes else 0.3) * w["WEIGHT_RUNES"] +
            (sentiment.confidence if sentiment else 0.3) * w["WEIGHT_SENTIMENT"] +
            (maeshowe.confidence if maeshowe else 0.3) * w["WEIGHT_MAESHOWE"]
        )
        # Pull toward 0.5 when confidence is low
        unified = unified * total_confidence + 0.5 * (1 - total_confidence)

        unified = max(0.0, min(1.0, unified))

        # Determine grade
        grade = self._grade(unified)

        # Determine action bias
        action, risk_mod = self._determine_action(unified, gaia, cosmos)

        # ── WAR COUNSEL ── Tactical intelligence from IRA, Guerrilla, War Strategy ──
        sentiment_details = sentiment.details if sentiment else {}
        counsel = self.war_counsel.get_counsel(unified, sentiment_details)
        tactical_mode = counsel.get("tactical_mode", "STANDARD")
        war_risk_mod = counsel.get("risk_modifier", 1.0)
        war_says = counsel.get("war_says", "")

        # Apply war counsel risk modifier (blend with action-based modifier)
        risk_mod = risk_mod * 0.6 + war_risk_mod * 0.4

        # ── Margin Oracle integration ──
        margin_rec = "NONE"
        margin_lev = 0
        margin_conv = 0.0
        if margin and margin.details:
            margin_rec = margin.details.get('direction', 'NONE')
            margin_lev = margin.details.get('leverage_rec', 0)
            margin_conv = margin.details.get('conviction', 0.0)
            # Only recommend margin when vision grade is strong enough
            if grade.value in ("FOG", "BLIND"):
                margin_rec = "NONE"
                margin_lev = 0
                margin_conv = 0.0

        # Generate prophecy
        prophecy = self._prophecy(unified, grade, gaia, cosmos, harmony,
                                  spirits, timeline, runes, sentiment, war_says,
                                  maeshowe)

        # Add margin insight to prophecy
        if margin_lev >= 2 and margin_rec != "NONE":
            prophecy += (f" MARGIN ORACLE: {margin_rec} at {margin_lev}x leverage "
                         f"(conviction {margin_conv:.0%}). "
                         f"Account health: {margin.phase if margin else 'unknown'}.")

        # Add Maeshowe lattice status to prophecy when in special states
        if maeshowe and maeshowe.details:
            gamma = maeshowe.details.get("gamma", 0.5)
            g_status = maeshowe.details.get("gamma_status", "ACTIVE_FIELD")
            if g_status == "LIGHTHOUSE":
                prophecy += (
                    f" MAESHOWE LIGHTHOUSE: Runic lattice Γ={gamma:.4f} — "
                    "circuit closed, dual-voice transmission complete."
                )
            elif g_status == "DEAD_FIELD":
                prophecy += (
                    f" MAESHOWE DEAD FIELD: Runic lattice Γ={gamma:.4f} — "
                    "below kill-switch threshold."
                )

        return SeerVision(
            timestamp=time.time(),
            unified_score=unified,
            grade=grade.value,
            gaia=gaia,
            cosmos=cosmos,
            harmony=harmony,
            spirits=spirits,
            timeline=timeline,
            runes=runes,
            sentiment=sentiment,
            margin=margin,
            maeshowe=maeshowe,
            prophecy=prophecy,
            action=action,
            risk_modifier=risk_mod,
            tactical_mode=tactical_mode,
            war_counsel=war_says,
            margin_recommendation=margin_rec,
            margin_leverage=margin_lev,
            margin_conviction=margin_conv,
        )

    def _grade(self, score: float) -> VisionGrade:
        if score >= SEER_CONFIG["DIVINE_CLARITY_THRESHOLD"]:
            return VisionGrade.DIVINE_CLARITY
        elif score >= SEER_CONFIG["CLEAR_SIGHT_THRESHOLD"]:
            return VisionGrade.CLEAR_SIGHT
        elif score >= SEER_CONFIG["PARTIAL_VISION_THRESHOLD"]:
            return VisionGrade.PARTIAL_VISION
        elif score >= SEER_CONFIG["FOG_THRESHOLD"]:
            return VisionGrade.FOG
        else:
            return VisionGrade.BLIND

    def _determine_action(self, unified: float, gaia: OracleReading,
                          cosmos: OracleReading) -> Tuple[str, float]:
        """Determine trading action bias and risk modifier."""
        if unified >= 0.80:
            return "BUY_BIAS", 1.2    # Increase position sizes
        elif unified >= 0.65:
            return "BUY_BIAS", 1.0    # Normal operation
        elif unified >= 0.50:
            return "HOLD", 0.8        # Slightly reduced
        elif unified >= 0.35:
            return "SELL_BIAS", 0.5   # Half positions
        else:
            return "DEFEND", 0.2      # Minimal exposure

    def _prophecy(self, unified: float, grade: VisionGrade,
                  gaia: OracleReading, cosmos: OracleReading,
                  harmony: OracleReading, spirits: OracleReading,
                  timeline: OracleReading,
                  runes: OracleReading = None,
                  sentiment: OracleReading = None,
                  war_says: str = "",
                  maeshowe: OracleReading = None) -> str:
        """Generate the Seer's prophecy."""
        parts = []

        if grade == VisionGrade.DIVINE_CLARITY:
            parts.append("The Seer sees with DIVINE CLARITY.")
            parts.append("All systems aligned - Earth, Cosmos, and Harmony resonate as one.")
            parts.append("The Queen may trade with full confidence.")
        elif grade == VisionGrade.CLEAR_SIGHT:
            parts.append("The Seer's vision is CLEAR.")
            parts.append(f"Gaia is in {gaia.phase}, Cosmos is {cosmos.phase}.")
            parts.append("Conditions favor careful engagement.")
        elif grade == VisionGrade.PARTIAL_VISION:
            parts.append("The Seer sees through PARTIAL FOG.")
            parts.append("Some Oracles disagree. Proceed with caution.")
        elif grade == VisionGrade.FOG:
            parts.append("FOG clouds the Seer's vision.")
            parts.append("The Oracles speak in contradictions. Reduce exposure.")
        else:
            parts.append("The Seer is BLIND.")
            parts.append("No coherence detected. The Queen should halt trading.")

        # Add dominant spirit
        spirit_name = spirits.details.get("dominant_node", "unknown")
        spirit_info = AURIS_NODES.get(spirit_name.upper(), {})
        if spirit_info:
            parts.append(
                f"The {spirit_info.get('spirit', '')} spirit ({spirit_name}) "
                f"governs this cycle through {spirit_info.get('domain', 'unknown')}."
            )

        # Add rune star-chart insight
        if runes and runes.details:
            active_count = runes.details.get("total_active", 0)
            dominant_rune = runes.details.get("dominant_rune", "None")
            dominant_glyph = runes.details.get("dominant_unicode", "")
            if active_count > 0:
                parts.append(
                    f"The star chart blazes with {active_count} active runes — "
                    f"{dominant_glyph} {dominant_rune} leads the constellation."
                )
            else:
                parts.append("The rune stones are silent — no star-chart geometry is active.")

        # Add sentiment / emotional intelligence
        if sentiment and sentiment.details:
            fg_label = sentiment.details.get("fg_label", "")
            fg_index = sentiment.details.get("fg_index", 50)
            flow_intent = sentiment.details.get("flow_intent", "QUIET")
            news_count = sentiment.details.get("news_headlines_count", 0)
            news_bearish = sentiment.details.get("news_bearish", 0)
            if fg_label:
                parts.append(f"Market emotion: {fg_label} (FGI={fg_index}).")
            if flow_intent != "QUIET":
                parts.append(f"Order flow: {flow_intent}.")
            if news_count > 0 and news_bearish > 0:
                parts.append(f"Geopolitics: {news_bearish}/{news_count} headlines bearish.")

        # Add Maeshowe runic lattice status
        if maeshowe and maeshowe.details:
            gamma      = maeshowe.details.get("gamma", 0.5)
            g_status   = maeshowe.details.get("gamma_status", "ACTIVE_FIELD")
            n_complete = maeshowe.details.get("n_complete", 0)
            n_total    = maeshowe.details.get("n_total", 13)
            mbeat      = maeshowe.details.get("master_beat_hz", 0.0)
            sch_mode   = maeshowe.details.get("schumann_mode", 4)
            sch_delta  = maeshowe.details.get("schumann_delta", 0.0)
            if g_status == "LIGHTHOUSE":
                parts.append(
                    f"Maeshowe LIGHTHOUSE (Γ={gamma:.4f}): the 4,800-year runic circuit "
                    f"is closed — {n_complete}/{n_total} inscriptions transmitting."
                )
            elif g_status == "ACTIVE_FIELD":
                parts.append(
                    f"Maeshowe ACTIVE FIELD (Γ={gamma:.4f}): "
                    f"{n_complete}/{n_total} runic voices transmitting. "
                    f"Master beat {mbeat:.2f} Hz — Schumann M{sch_mode} "
                    f"Δ{sch_delta:.2f} Hz. Nr.15 pivot: bring two voices."
                )
            else:
                parts.append(
                    f"Maeshowe DEAD FIELD (Γ={gamma:.4f}): lattice below kill-switch."
                )

        # Add war counsel
        if war_says:
            parts.append(f"War Counsel: {war_says[:200]}")

        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# THE PROPHECY ENGINE - Consensus with Queen & King
# ═══════════════════════════════════════════════════════════════════════════

class ProphecyEngine:
    """
    Generates consensus between the three pillars:
    Queen (trading cognition), King (financial health), Seer (cosmic coherence).
    """

    def generate_consensus(self, vision: SeerVision,
                           queen_confidence: float = 0.5,
                           king_health: str = "STABLE") -> SeerConsensus:
        """Generate a three-pillar consensus."""

        # Map king health to numeric
        king_scores = {
            "SOVEREIGN": 0.9, "PROSPEROUS": 0.75,
            "STABLE": 0.55, "STRAINED": 0.35, "BANKRUPT": 0.1,
        }
        king_score = king_scores.get(king_health, 0.5)

        # Three-way average (equal weight - each pillar is autonomous)
        alignment = (vision.unified_score + queen_confidence + king_score) / 3.0

        # Consensus action
        if alignment >= 0.75 and min(vision.unified_score, queen_confidence, king_score) >= 0.5:
            action = "STRONG_BUY"
        elif alignment >= 0.60:
            action = "BUY"
        elif alignment >= 0.45:
            action = "HOLD"
        elif alignment >= 0.30:
            action = "SELL"
        elif alignment >= 0.15:
            action = "STRONG_SELL"
        else:
            action = "HALT"

        # Override: if any pillar is critical, escalate
        if king_health == "BANKRUPT":
            action = "HALT"
        if vision.grade in ["BLIND"]:
            if action in ["STRONG_BUY", "BUY"]:
                action = "HOLD"

        return SeerConsensus(
            timestamp=time.time(),
            seer_grade=vision.grade,
            queen_confidence=queen_confidence,
            king_health=king_health,
            consensus_action=action,
            alignment_score=alignment,
        )


# ═══════════════════════════════════════════════════════════════════════════
# AUREON THE SEER - The Third Pillar
# ═══════════════════════════════════════════════════════════════════════════

class AureonTheSeer:
    """
    AUREON THE SEER: Autonomous Coherence & Cosmic Intelligence.

    The third pillar of the Aureon Triumvirate.
    Perceives reality through 6 Oracles, combines them through the
    All-Seeing Eye, and generates consensus with Queen and King.

    Usage:
        seer = get_seer()
        vision = seer.see()
        print(vision.prophecy)
        print(f"Grade: {vision.grade}, Action: {vision.action}")

        consensus = seer.get_consensus(queen_confidence=0.7, king_health="PROSPEROUS")
        print(f"Consensus: {consensus.consensus_action}")
    """

    def __init__(self):
        # The 8 Oracles
        self.oracle_gaia = OracleOfGaia()
        self.oracle_cosmos = OracleOfCosmos()
        self.oracle_harmony = OracleOfHarmony()
        self.oracle_spirits = OracleOfSpirits()
        self.oracle_time = OracleOfTime()
        self.oracle_runes = OracleOfRunes()
        self.oracle_sentiment = OracleOfSentiment()  # 7th Oracle: Fear/Greed + News + Velocity
        self.oracle_margin = OracleOfMargin()        # 8th Oracle: Kraken margin opportunity
        self.oracle_maeshowe = OracleOfMaeshowe()    # 9th Oracle: Maeshowe transmission lattice

        # The All-Seeing Eye
        self.eye = AllSeeingEye()

        # The Prophecy Engine
        self.prophecy_engine = ProphecyEngine()

        # Vision history
        self.vision_history: deque = deque(maxlen=SEER_CONFIG["HISTORY_SIZE"])
        self.latest_vision: Optional[SeerVision] = None

        # Autonomous monitoring
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Context data (fed by ecosystem)
        self._positions: Dict = {}
        self._ticker_cache: Dict = {}
        self._market_data: Dict = {}
        self._trade_history: List = []
        self._wave_ctx: dict = {}   # Ocean wave scanner — bot frequency signatures

        logger.info("Aureon the Seer has awakened. The Third Pillar stands. 9 Oracles active.")

    # ─────────────────────────────────────────────────────────
    # Perception - The Seer Sees
    # ─────────────────────────────────────────────────────────

    def see(self) -> SeerVision:
        """
        Take a complete reading from all 9 Oracles and combine
        into a unified vision. This is the Seer's primary method.
        """
        with self._lock:
            gaia = self.oracle_gaia.read()
            cosmos = self.oracle_cosmos.read()
            harmony = self.oracle_harmony.read(self._positions, self._ticker_cache, self._wave_ctx)
            spirits = self.oracle_spirits.read(self._market_data)
            timeline = self.oracle_time.read(self._trade_history)
            runes = self.oracle_runes.read()
            sentiment = self.oracle_sentiment.read(self._market_data)
            maeshowe = self.oracle_maeshowe.read()  # 9th Oracle: Maeshowe lattice Γ

            # 8th Oracle: Margin — needs current vision score + trend
            # Use a preliminary score from the first 8 oracles (excl. margin)
            w = SEER_CONFIG
            _prelim_score = (
                gaia.score * w["WEIGHT_GAIA"] +
                cosmos.score * w["WEIGHT_COSMOS"] +
                harmony.score * w["WEIGHT_HARMONY"] +
                spirits.score * w["WEIGHT_SPIRITS"] +
                timeline.score * w["WEIGHT_TIME"] +
                (runes.score if runes else 0.5) * w["WEIGHT_RUNES"] +
                (sentiment.score if sentiment else 0.5) * w["WEIGHT_SENTIMENT"] +
                (maeshowe.score if maeshowe else 0.5) * w["WEIGHT_MAESHOWE"]
            )
            _trend_info = self.get_trend()
            _trend = _trend_info.get('trend', 'STABLE')
            margin = self.oracle_margin.read(
                market_data=self._market_data,
                vision_score=_prelim_score,
                trend=_trend,
            )

            vision = self.eye.combine(gaia, cosmos, harmony, spirits, timeline,
                                      runes, sentiment, margin, maeshowe)
            self.latest_vision = vision
            self.vision_history.append(vision)

            # Log the vision
            self._log_vision(vision)

            return vision

    def get_consensus(self, queen_confidence: float = 0.5,
                      king_health: str = "STABLE") -> SeerConsensus:
        """Get three-pillar consensus between Queen, King, and Seer."""
        if self.latest_vision is None:
            self.see()
        return self.prophecy_engine.generate_consensus(
            self.latest_vision, queen_confidence, king_health
        )

    # ─────────────────────────────────────────────────────────
    # Context Updates - Feed the Seer
    # ─────────────────────────────────────────────────────────

    def update_context(self, positions: Dict = None,
                       ticker_cache: Dict = None,
                       market_data: Dict = None,
                       trade_history: List = None):
        """Update the Seer's context with live ecosystem data."""
        with self._lock:
            if positions is not None:
                self._positions = positions
            if ticker_cache is not None:
                self._ticker_cache = ticker_cache
            if market_data is not None:
                self._market_data = market_data
            if trade_history is not None:
                self._trade_history = trade_history

    def inject_wave_context(self, wave_data: dict) -> None:
        """
        Feed ocean wave scanner results into the Seer's Oracles.
        Called by MultiverseLearningBridge after every WaveformAnalyzer scan.
        OracleOfHarmony reads bot frequency signatures from this context.
        """
        with self._lock:
            self._wave_ctx = dict(wave_data) if wave_data else {}

    # ─────────────────────────────────────────────────────────
    # Autonomous Operation - The Seer Never Sleeps
    # ─────────────────────────────────────────────────────────

    def start_autonomous(self):
        """Start the Seer's autonomous scanning loop + prediction validator."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._autonomous_loop, daemon=True, name="AureonTheSeer"
        )
        self._monitor_thread.start()

        # Start omnipresent prediction validator alongside the main loop
        self._validator_thread = threading.Thread(
            target=self._prediction_validator_loop, daemon=True,
            name="SeerPredictionValidator"
        )
        self._validator_thread.start()
        logger.info("Aureon the Seer is watching. Autonomous perception + prediction validation engaged.")

    def stop_autonomous(self):
        """Stop autonomous scanning."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("The Seer rests.")

    def _autonomous_loop(self):
        """Background loop: periodic oracle readings."""
        while self._running:
            try:
                self.see()
                time.sleep(SEER_CONFIG["SCAN_INTERVAL_SEC"])
            except Exception as e:
                logger.error(f"Seer autonomous loop error: {e}")
                time.sleep(10)

    # ─────────────────────────────────────────────────────────
    # OMNIPRESENT PREDICTION VALIDATION
    # Continuously checks if past SEER buy-predictions came true
    # using open-source real market data (no API keys needed).
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────────────
    # Timeframe definitions — mirror those in orca_fire_trade.py
    # ─────────────────────────────────────────────────────────────────
    _TIMEFRAME_LAYERS = [
        ("1m",    60),         ("5m",    300),
        ("30m",   1_800),      ("1h",    3_600),
        ("2h",    7_200),      ("3h",    10_800),
        ("6h",    21_600),     ("12h",   43_200),
        ("24h",   86_400),     ("48h",   172_800),
        ("1w",    604_800),    ("2w",    1_209_600),
        ("1mo",   2_592_000),  ("3mo",   7_776_000),
        ("6mo",   15_552_000), ("1y",    31_536_000),
    ]
    _TIMEFRAME_DICT  = dict(_TIMEFRAME_LAYERS)        # label → seconds
    _ACCURACY_FILE   = "seer_prediction_accuracy.json"
    _TF_ACCURACY_FILE = "seer_timeframe_accuracy.json"
    _PREDICTION_FILE  = "seer_trade_predictions.jsonl"
    _VALIDATE_AFTER_SEC = 60    # minimum age before any layer is checked
    _VALIDATOR_INTERVAL = 300   # validator runs every 5 minutes

    def _prediction_validator_loop(self):
        """Background thread: validate SEER trade predictions against real prices."""
        import time as _t
        _t.sleep(60)   # let the engine fully boot first
        while self._running:
            try:
                self._validate_pending_predictions()
            except Exception as _ve:
                logger.error(f"[SeerValidator] error: {_ve}")
            _t.sleep(self._VALIDATOR_INTERVAL)

    def _fetch_open_source_price(self, symbol: str) -> float:
        """
        Fetch current price for a symbol via open-source APIs.
        Priority: Binance public → CoinGecko → Kraken public.
        Returns 0.0 on failure (no API keys needed).
        """
        try:
            import urllib.request as _ur
            import json as _j

            sym = symbol.upper().replace("/", "").replace("-", "")
            for q in ("USDC", "USDT", "USD", "GBP", "EUR", "BUSD", "TUSD"):
                if sym.endswith(q):
                    base = sym[:-len(q)]
                    break
            else:
                base = sym

            _aliasmap = {
                "XBT": "BTC", "XXBT": "BTC", "XETH": "ETH",
                "XXLM": "XLM", "XXRP": "XRP",
            }
            base = _aliasmap.get(base, base)

            # 1. Binance public
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={base}USDT"
            with _ur.urlopen(url, timeout=6) as r:
                price = float(_j.loads(r.read().decode()).get("price", 0))
            if price > 0:
                return price
        except Exception:
            pass
        try:
            # 2. CoinGecko
            import urllib.request as _ur
            import json as _j
            _cg_aliases = {
                "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
                "ada": "cardano", "xrp": "ripple", "dot": "polkadot",
                "link": "chainlink", "avax": "avalanche-2", "atom": "cosmos",
                "bch": "bitcoin-cash", "ltc": "litecoin", "bnb": "binancecoin",
            }
            cg_id = _cg_aliases.get(base.lower(), base.lower())
            url = (f"https://api.coingecko.com/api/v3/simple/price"
                   f"?ids={cg_id}&vs_currencies=usd")
            with _ur.urlopen(url, timeout=8) as r:
                price = float(_j.loads(r.read().decode()).get(cg_id, {}).get("usd", 0))
            if price > 0:
                return price
        except Exception:
            pass
        try:
            # 3. Kraken public
            import urllib.request as _ur
            import json as _j
            kraken_sym = "XBTUSD" if base == "BTC" else f"{base}USD"
            url = f"https://api.kraken.com/0/public/Ticker?pair={kraken_sym}"
            with _ur.urlopen(url, timeout=6) as r:
                result = _j.loads(r.read().decode()).get("result", {})
            if result:
                price = float(next(iter(result.values())).get("c", [0])[0])
                if price > 0:
                    return price
        except Exception:
            pass
        return 0.0

    def _ensure_timeframe_layers(self, pred: dict) -> bool:
        """
        Back-fill timeframe_layers onto any legacy prediction that lacks them.
        Returns True if layers were added (pred mutated in place).
        """
        if "timeframe_layers" in pred and pred["timeframe_layers"]:
            return False

        import time as _t
        try:
            pred_time = datetime.fromisoformat(pred.get("timestamp", "")).timestamp()
        except Exception:
            pred_time = _t.time()

        is_bullish = pred.get("symbol_signal", {}).get("bullish", True)
        pred["timeframe_layers"] = [
            {
                "label":       label,
                "seconds":     secs,
                "validate_at": pred_time + secs,
                "is_bullish":  is_bullish,
                "validated":   False,
                "outcome":     None,
                "price_at":    None,
                "pct_change":  None,
            }
            for label, secs in self._TIMEFRAME_LAYERS
        ]
        return True

    def _validate_pending_predictions(self):
        """
        Read seer_trade_predictions.jsonl, validate any layer whose horizon
        has passed, rewrite atomically, and update accuracy stats.

        Each prediction carries 16 timeframe_layers (1m → 1y).
        A layer is checked when now >= layer["validate_at"].
        The top-level validated/outcome is set when the LAST layer resolves.
        """
        import time as _t
        import json as _j

        if not os.path.exists(self._PREDICTION_FILE):
            return

        with open(self._PREDICTION_FILE, "r") as fh:
            raw_lines = [l.strip() for l in fh if l.strip()]

        predictions = []
        for line in raw_lines:
            try:
                predictions.append(_j.loads(line))
            except Exception:
                pass

        if not predictions:
            return

        now  = _t.time()
        any_changed = False
        price_cache: Dict[str, float] = {}

        for pred in predictions:
            # Back-fill legacy predictions that have no timeframe_layers
            if self._ensure_timeframe_layers(pred):
                any_changed = True

            layers = pred.get("timeframe_layers", [])
            # Use buy_price_usd if available (GBP pairs need USD-normalized comparison)
            buy_price = float(pred.get("buy_price_usd", 0) or pred.get("buy_price", 0) or 0)
            if buy_price <= 0:
                continue

            # Back-fill buy_price_usd for legacy GBP predictions
            if "buy_price_usd" not in pred and pred.get("exchange") == "kraken":
                pair_str = (pred.get("pair") or "").upper()
                if "GBP" in pair_str:
                    raw_gbp = float(pred.get("buy_price", 0) or 0)
                    if raw_gbp > 0:
                        try:
                            import urllib.request as _u_fx
                            _fx_r = _u_fx.urlopen('https://api.binance.com/api/v3/ticker/price?symbol=GBPUSDT', timeout=5)
                            gbp_rate = float(_j.loads(_fx_r.read().decode()).get('price', 1.27))
                        except Exception:
                            gbp_rate = 1.27
                        buy_price = round(raw_gbp * gbp_rate, 6)
                        pred["buy_price_usd"] = buy_price
                        pred["quote_currency"] = "GBP"
                        any_changed = True
                        logger.info(f"[SeerValidator] Back-filled buy_price_usd for {pred.get('pair')}: £{raw_gbp:.2f} → ${buy_price:.2f}")

            # Resolve each layer whose validate_at has passed
            for layer in layers:
                if layer.get("validated"):
                    continue
                if now < float(layer.get("validate_at", now + 1)):
                    continue  # horizon not reached yet

                # Fetch price (cache per symbol per validation run)
                sym_signal  = pred.get("symbol_signal", {})
                ticker_sym  = sym_signal.get("symbol", pred.get("pair", ""))
                if not ticker_sym:
                    continue
                if ticker_sym not in price_cache:
                    price_cache[ticker_sym] = self._fetch_open_source_price(ticker_sym)

                current_price = price_cache[ticker_sym]
                if current_price <= 0:
                    continue  # can't validate this layer right now

                pct = (current_price - buy_price) / buy_price * 100
                is_bullish = layer.get("is_bullish", True)

                if is_bullish and pct >= 0.1:
                    outcome = "HIT"
                elif is_bullish and pct <= -0.1:
                    outcome = "MISS"
                elif not is_bullish and pct <= -0.1:
                    outcome = "HIT"
                elif not is_bullish and pct >= 0.1:
                    outcome = "MISS"
                else:
                    outcome = "NEUTRAL"

                layer["validated"]  = True
                layer["outcome"]    = outcome
                layer["price_at"]   = current_price
                layer["pct_change"] = round(pct, 4)
                any_changed = True

                logger.info(
                    f"[SeerValidator] {pred.get('pair')} @{layer['label']}: "
                    f"buy={buy_price:.6g} now={current_price:.6g} "
                    f"({pct:+.2f}%) → {outcome}"
                )

            # Mark overall validated only when ALL layers are done
            all_done = all(l.get("validated") for l in layers)
            if all_done and not pred.get("validated"):
                last_layer = layers[-1] if layers else {}
                pred["validated"] = True
                pred["outcome"]   = last_layer.get("outcome", "NEUTRAL")
                any_changed = True

        if any_changed:
            tmp = self._PREDICTION_FILE + ".tmp"
            with open(tmp, "w") as fh:
                for p in predictions:
                    fh.write(_j.dumps(p) + "\n")
            os.replace(tmp, self._PREDICTION_FILE)
            self._update_prediction_accuracy_stats(predictions)
            self._update_timeframe_accuracy_stats(predictions)

    def _update_prediction_accuracy_stats(self, predictions: list):
        """Recompute and persist overall prediction accuracy stats."""
        import json as _j

        validated = [p for p in predictions if p.get("validated")]
        total   = len(validated)
        hits    = sum(1 for p in validated if p.get("outcome") == "HIT")
        misses  = sum(1 for p in validated if p.get("outcome") == "MISS")
        neutral = sum(1 for p in validated if p.get("outcome") == "NEUTRAL")
        pending = sum(1 for p in predictions if not p.get("validated"))
        accuracy = hits / total if total > 0 else 0.0

        by_exchange: Dict[str, Dict] = {}
        for p in validated:
            ex = p.get("exchange", "unknown")
            if ex not in by_exchange:
                by_exchange[ex] = {"hits": 0, "misses": 0, "neutral": 0}
            o = p.get("outcome", "NEUTRAL").upper()
            if o == "HIT":
                by_exchange[ex]["hits"] += 1
            elif o == "MISS":
                by_exchange[ex]["misses"] += 1
            else:
                by_exchange[ex]["neutral"] += 1

        stats = {
            "last_updated":    datetime.now().isoformat(),
            "total_validated": total,
            "pending":         pending,
            "hits":            hits,
            "misses":          misses,
            "neutral":         neutral,
            "accuracy_pct":    round(accuracy * 100, 2),
            "by_exchange":     by_exchange,
        }
        tmp = self._ACCURACY_FILE + ".tmp"
        with open(tmp, "w") as fh:
            _j.dump(stats, fh, indent=2)
        os.replace(tmp, self._ACCURACY_FILE)

        logger.info(
            f"[SeerValidator] Overall accuracy: {accuracy*100:.1f}% "
            f"({hits}H/{misses}M/{neutral}N from {total} fully validated, {pending} pending)"
        )

    def _update_timeframe_accuracy_stats(self, predictions: list):
        """
        Recompute per-timeframe-layer accuracy and write
        seer_timeframe_accuracy.json — the timeline accuracy map.
        """
        import json as _j

        # Accumulate hits/misses/neutral per label
        tf_stats: Dict[str, Dict] = {}
        for label, _ in self._TIMEFRAME_LAYERS:
            tf_stats[label] = {"hits": 0, "misses": 0, "neutral": 0,
                                "validated": 0, "pending": 0}

        for pred in predictions:
            for layer in pred.get("timeframe_layers", []):
                label = layer.get("label", "?")
                if label not in tf_stats:
                    tf_stats[label] = {"hits": 0, "misses": 0, "neutral": 0,
                                        "validated": 0, "pending": 0}
                if layer.get("validated"):
                    tf_stats[label]["validated"] += 1
                    o = (layer.get("outcome") or "NEUTRAL").upper()
                    if o == "HIT":
                        tf_stats[label]["hits"] += 1
                    elif o == "MISS":
                        tf_stats[label]["misses"] += 1
                    else:
                        tf_stats[label]["neutral"] += 1
                else:
                    tf_stats[label]["pending"] += 1

        # Compute accuracy & format for easy reading
        timeline = []
        for label, secs in self._TIMEFRAME_LAYERS:
            s = tf_stats.get(label, {})
            v = s.get("validated", 0)
            h = s.get("hits", 0)
            acc = round(h / v * 100, 2) if v > 0 else None
            timeline.append({
                "label":       label,
                "seconds":     secs,
                "validated":   v,
                "pending":     s.get("pending", 0),
                "hits":        h,
                "misses":      s.get("misses", 0),
                "neutral":     s.get("neutral", 0),
                "accuracy_pct": acc,
            })

        output = {
            "last_updated": datetime.now().isoformat(),
            "description":  "SEER prediction accuracy layered by time horizon (1m → 1y)",
            "total_predictions": len(predictions),
            "timeline": timeline,
        }

        tmp = self._TF_ACCURACY_FILE + ".tmp"
        with open(tmp, "w") as fh:
            _j.dump(output, fh, indent=2)
        os.replace(tmp, self._TF_ACCURACY_FILE)

        # Print summary to engine log
        lines = ["[SeerValidator] ── Timeframe Accuracy Map ──"]
        for row in timeline:
            if row["validated"] > 0:
                bar = "█" * int((row["accuracy_pct"] or 0) / 10)
                lines.append(
                    f"  {row['label']:>4s}  {bar:<10s} {row['accuracy_pct']:5.1f}%  "
                    f"({row['hits']}H/{row['misses']}M/{row['neutral']}N "
                    f"of {row['validated']} validated, {row['pending']} pending)"
                )
            else:
                lines.append(
                    f"  {row['label']:>4s}  {'':10s}  --.--%  "
                    f"(0 validated, {row['pending']} pending)"
                )
        logger.info("\n".join(lines))

    # ─────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────

    def get_vision_summary(self) -> Dict[str, Any]:
        """Get a summary of the latest vision."""
        v = self.latest_vision
        if not v:
            return {"status": "no_vision", "message": "The Seer has not yet opened its eyes."}

        def _oracle_dict(o):
            if not o:
                return None
            return {
                "score": o.score,
                "phase": o.phase,
                "signal": o.dominant_signal,
                "details": dict(o.details or {}),
            }

        summary = {
            "timestamp": datetime.fromtimestamp(v.timestamp).isoformat(),
            "unified_score": v.unified_score,
            "grade": v.grade,
            "action": v.action,
            "risk_modifier": v.risk_modifier,
            "tactical_mode": v.tactical_mode,
            "war_counsel": v.war_counsel,
            "prophecy": v.prophecy,
            "oracles": {
                "gaia": _oracle_dict(v.gaia),
                "cosmos": _oracle_dict(v.cosmos),
                "harmony": _oracle_dict(v.harmony),
                "spirits": _oracle_dict(v.spirits),
                "timeline": _oracle_dict(v.timeline),
                "runes": _oracle_dict(v.runes) if hasattr(v, 'runes') else None,
                "sentiment": _oracle_dict(v.sentiment) if hasattr(v, 'sentiment') else None,
                "margin": _oracle_dict(v.margin) if hasattr(v, 'margin') else None,
                "maeshowe": _oracle_dict(v.maeshowe) if hasattr(v, 'maeshowe') else None,
            },
            "margin_recommendation": getattr(v, 'margin_recommendation', 'NONE'),
            "margin_leverage": getattr(v, 'margin_leverage', 0),
            "margin_conviction": getattr(v, 'margin_conviction', 0.0),
        }
        # Backward-compatible top-level alias used by bridges that consume
        # dict summaries rather than the SeerVision dataclass.
        summary["runes"] = summary["oracles"].get("runes")
        return summary

    def get_trend(self, window: int = 10) -> Dict[str, Any]:
        """Get the trend of the Seer's unified score over recent readings."""
        recent = list(self.vision_history)[-window:]
        if len(recent) < 2:
            return {"trend": "INSUFFICIENT_DATA", "readings": len(recent)}

        scores = [v.unified_score for v in recent]
        first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
        second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        delta = second_half - first_half

        if delta > 0.05:
            trend = "IMPROVING"
        elif delta < -0.05:
            trend = "DECLINING"
        else:
            trend = "STABLE"

        return {
            "trend": trend,
            "delta": delta,
            "current": scores[-1],
            "average": sum(scores) / len(scores),
            "readings": len(scores),
        }

    # ─────────────────────────────────────────────────────────
    # Reports
    # ─────────────────────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a human-readable Seer report."""
        v = self.latest_vision
        if not v:
            return "The Seer has not yet opened its eyes. Call see() first."

        sym = "£" if os.getenv("BASE_CURRENCY", "GBP") == "GBP" else "$"
        lines = [
            "=" * 60,
            "AUREON THE SEER - VISION REPORT",
            f"Time: {datetime.fromtimestamp(v.timestamp).strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            f"UNIFIED SCORE:  {v.unified_score:.2f}",
            f"VISION GRADE:   {v.grade}",
            f"ACTION BIAS:    {v.action}",
            f"RISK MODIFIER:  {v.risk_modifier:.1f}x",
            "",
            "ORACLE READINGS:",
            "-" * 40,
        ]

        for name, oracle in [("Gaia", v.gaia), ("Cosmos", v.cosmos),
                             ("Harmony", v.harmony), ("Spirits", v.spirits),
                             ("Timeline", v.timeline),
                             ("Runes", getattr(v, 'runes', None)),
                             ("Sentiment", getattr(v, 'sentiment', None))]:
            if oracle:
                lines.append(
                    f"  {name:12s} | Score: {oracle.score:.2f} | "
                    f"Phase: {oracle.phase:16s} | {oracle.dominant_signal}"
                )

        if v.tactical_mode:
            lines.append(f"\nTACTICAL MODE:  {v.tactical_mode}")
        if v.war_counsel:
            lines.append(f"WAR COUNSEL:    {v.war_counsel}")

        trend = self.get_trend()
        lines.extend([
            "",
            f"TREND: {trend.get('trend', 'N/A')} (delta: {trend.get('delta', 0):+.3f})",
            "",
            "PROPHECY:",
            v.prophecy,
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────

    def _log_vision(self, vision: SeerVision):
        """Append vision to the log file."""
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(vision.timestamp).isoformat(),
                "score": vision.unified_score,
                "grade": vision.grade,
                "action": vision.action,
                "risk_mod": vision.risk_modifier,
                "tactical_mode": vision.tactical_mode,
                "oracles": {
                    "gaia": vision.gaia.score if vision.gaia else None,
                    "cosmos": vision.cosmos.score if vision.cosmos else None,
                    "harmony": vision.harmony.score if vision.harmony else None,
                    "spirits": vision.spirits.score if vision.spirits else None,
                    "timeline": vision.timeline.score if vision.timeline else None,
                    "runes": vision.runes.score if hasattr(vision, 'runes') and vision.runes else None,
                    "sentiment": vision.sentiment.score if hasattr(vision, 'sentiment') and vision.sentiment else None,
                    "margin": vision.margin.score if hasattr(vision, 'margin') and vision.margin else None,
                },
                "margin_recommendation": getattr(vision, 'margin_recommendation', 'NONE'),
                "margin_leverage": getattr(vision, 'margin_leverage', 0),
            }
            with open(SEER_CONFIG["VISION_LOG"], "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON - The Seer is One
# ═══════════════════════════════════════════════════════════════════════════

_seer_instance: Optional[AureonTheSeer] = None


def get_seer() -> AureonTheSeer:
    """Get the singleton Seer instance."""
    global _seer_instance
    if _seer_instance is None:
        _seer_instance = AureonTheSeer()
    return _seer_instance
