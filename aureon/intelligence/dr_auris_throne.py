#!/usr/bin/env python3
"""
Dr. Auris Throne -- Planetary Harmonic Intelligence Engine

Dr. Auris Throne is the HNC research intelligence of the Aureon system.
She processes live planetary and solar data (NOAA, NASA, Schumann),
interprets it through the HNC Master Formula, and communicates
harmonic intelligence to the Queen via the ThoughtBus.

Where the Queen (Sero) decides, Dr. Auris Throne understands.

Data Sources:
    - NOAA SWPC: Kp index, solar wind, Bz component, geomagnetic forecasts
    - NASA DONKI: Solar flares, CMEs
    - Schumann resonance: 7.83 Hz fundamental + harmonics
    - Planetary harmonic sweep: FFT entity coordination signatures
    - Earth resonance engine: Trading gate coherence

Output:
    - Publishes auris.throne.* topics to ThoughtBus every cycle
    - auris.throne.cosmic_state -- unified planetary assessment
    - auris.throne.advisory -- recommendations for the Queen
    - auris.throne.alert -- urgent cosmic events (storms, CMEs, etc.)

Architecture:
    Live Planetary Data (NOAA/NASA/Schumann)
        |
        v
    Dr. Auris Throne (this file)
        |
        +-- Space Weather Analysis (Kp, solar wind, Bz, flares)
        +-- Schumann Resonance Monitoring (7.83 Hz + harmonics)
        +-- Lambda Engine Processing (HNC Master Formula)
        +-- Cosmic Alignment Scoring (sacred frequencies + geometry)
        |
        v
    ThoughtBus: auris.throne.* topics
        |
        v
    Queen Cortex (Alpha/Theta bands) --> Queen Decisions

Gary Leckey & Tina Brown | April 2026 | The Research Intelligence
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Sacred constants
PHI = 1.618033988749895
PHI_SQUARED = PHI ** 2  # 2.618 -- the chain from Sumer to Now
SCHUMANN_HZ = 7.83
LOVE_HZ = 528.0
CROWN_HZ = 963.0


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CosmicState:
    """Dr. Auris Throne's unified assessment of planetary conditions."""
    # Space weather
    kp_index: float = 0.0             # 0-9 geomagnetic activity
    kp_category: str = "Quiet"        # Quiet, Active, Storm, Severe
    solar_wind_speed: float = 0.0     # km/s
    bz_component: float = 0.0         # nT (negative = substorm risk)
    solar_flares_24h: int = 0
    geomagnetic_forecast: str = ""

    # Schumann resonance
    schumann_hz: float = 7.83         # Fundamental frequency
    schumann_coherence: float = 0.5   # 0-1 field coherence
    schumann_amplitude: float = 0.0   # Signal strength
    earth_disturbance: float = 0.0    # 0-1 (0=calm, 1=disturbed)
    earth_blessing: float = 0.5       # 0-1 (how favorable for trading)

    # HNC Lambda
    lambda_t: float = 0.0             # Master equation value
    consciousness_psi: float = 0.0    # 0-1 consciousness level
    coherence_gamma: float = 0.0      # 0-1 (target >= 0.945)
    consciousness_level: str = "DORMANT"

    # Cosmic alignment
    cosmic_score: float = 0.5         # 0-1 overall cosmic favorability
    alignment_details: Dict[str, float] = field(default_factory=dict)

    # Advisory
    gate_open: bool = True            # Should we trade?
    advisory: str = "OBSERVE"         # TRADE, OBSERVE, PROTECT, SLEEP
    reasoning: List[str] = field(default_factory=list)
    timestamp: float = 0.0


# ============================================================================
# DR. AURIS THRONE ENGINE
# ============================================================================

class DrAurisThrone:
    """
    The Planetary Harmonic Intelligence Engine.

    Gathers live data from NOAA, NASA, Schumann monitors, and the
    HNC Lambda Engine, synthesizes it into a unified cosmic state,
    and publishes harmonic intelligence to the ThoughtBus for the Queen.
    """

    def __init__(self, cycle_interval: float = 10.0):
        self._cycle_interval = cycle_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycle_count = 0
        self._state = CosmicState()

        # ThoughtBus
        self._thought_bus = None
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
        except Exception:
            pass

        # Lambda Engine (HNC Master Formula)
        self._lambda_engine = None
        try:
            from aureon.core.aureon_lambda_engine import LambdaEngine
            self._lambda_engine = LambdaEngine()
        except Exception:
            pass

        # Space Weather Bridge (NOAA/NASA)
        self._space_weather_fn = None
        try:
            from aureon.data_feeds.aureon_space_weather_bridge import get_cosmic_alignment_from_space_weather
            self._space_weather_fn = get_cosmic_alignment_from_space_weather
        except Exception:
            pass

        # Schumann Resonance Bridge
        self._schumann_fn = None
        try:
            from aureon.harmonic.aureon_schumann_resonance_bridge import get_earth_blessing
            self._schumann_fn = get_earth_blessing
        except Exception:
            pass

        # Full Schumann reading
        self._schumann_reading_fn = None
        try:
            from aureon.harmonic.aureon_schumann_resonance_bridge import get_schumann_reading
            self._schumann_reading_fn = get_schumann_reading
        except Exception:
            pass

        # Earth Resonance Engine (trading gate)
        self._earth_gate_fn = None
        try:
            from aureon.harmonic.earth_resonance_engine import get_earth_engine
            engine = get_earth_engine()
            self._earth_gate_fn = engine.get_trading_gate_status
        except Exception:
            pass

        logger.info("[DR. AURIS THRONE] Planetary Harmonic Intelligence Engine initialized")

    # ================================================================
    # LIFECYCLE
    # ================================================================

    def start(self) -> None:
        """Start the Dr. Auris Throne background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._throne_loop,
            name="DrAurisThrone",
            daemon=True,
        )
        self._thread.start()
        logger.info("[DR. AURIS THRONE] Planetary monitoring STARTED (cycle=%ss)", self._cycle_interval)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)

    # ================================================================
    # MAIN LOOP
    # ================================================================

    def _throne_loop(self) -> None:
        """Main loop: gather planetary data, analyze, publish."""
        while self._running:
            cycle_start = time.time()
            self._cycle_count += 1

            try:
                state = self._analyze_cosmos()
                self._state = state
                self._publish_state(state)

                # Publish alert if conditions are extreme
                if state.kp_index >= 5 or state.earth_disturbance > 0.7 or state.bz_component < -10:
                    self._publish_alert(state)

            except Exception as e:
                logger.debug(f"Dr. Auris Throne cycle error: {e}")

            elapsed = time.time() - cycle_start
            sleep_time = max(0, self._cycle_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ================================================================
    # COSMIC ANALYSIS
    # ================================================================

    def _analyze_cosmos(self) -> CosmicState:
        """Gather all planetary data and synthesize into a unified assessment."""
        state = CosmicState(timestamp=time.time())
        reasoning = []

        # --- 1. Space Weather (NOAA/NASA) ---
        if self._space_weather_fn:
            try:
                sw = self._space_weather_fn()
                if isinstance(sw, dict):
                    state.kp_index = sw.get("kp_index", 0)
                    state.kp_category = sw.get("kp_category", "Quiet")
                    state.solar_wind_speed = sw.get("solar_wind_speed", 0)
                    state.bz_component = sw.get("bz_component", 0)
                    state.solar_flares_24h = sw.get("solar_flares_24h", 0)
                    state.geomagnetic_forecast = sw.get("geomagnetic_storm_3day", "")
                    state.cosmic_score = sw.get("cosmic_score", 0.5)

                    if state.kp_index >= 5:
                        reasoning.append(f"Geomagnetic storm: Kp={state.kp_index} ({state.kp_category})")
                    if state.bz_component < -5:
                        reasoning.append(f"Southward Bz ({state.bz_component:.1f} nT) — substorm risk")
                    if state.solar_flares_24h > 0:
                        reasoning.append(f"{state.solar_flares_24h} solar flares in 24h")
                elif isinstance(sw, (int, float)):
                    state.cosmic_score = float(sw)
            except Exception as e:
                logger.debug(f"Space weather unavailable: {e}")

        # --- 2. Schumann Resonance ---
        if self._schumann_fn:
            try:
                blessing, msg = self._schumann_fn()
                state.earth_blessing = blessing
                if blessing < 0.4:
                    reasoning.append(f"Earth field disturbed (blessing={blessing:.2f})")
                elif blessing > 0.7:
                    reasoning.append(f"Earth field coherent (blessing={blessing:.2f})")
            except Exception:
                pass

        if self._schumann_reading_fn:
            try:
                reading = self._schumann_reading_fn()
                if isinstance(reading, dict):
                    state.schumann_hz = reading.get("fundamental_hz", 7.83)
                    state.schumann_coherence = reading.get("coherence", 0.5)
                    state.schumann_amplitude = reading.get("amplitude", 0)
                    state.earth_disturbance = reading.get("earth_disturbance_level", 0)
                elif hasattr(reading, "fundamental_hz"):
                    state.schumann_hz = getattr(reading, "fundamental_hz", 7.83)
                    state.schumann_coherence = getattr(reading, "quality", 0.5)
                    state.schumann_amplitude = getattr(reading, "amplitude", 0)
                    state.earth_disturbance = getattr(reading, "earth_disturbance_level", 0)
            except Exception:
                pass

        # --- 3. Earth Resonance Gate ---
        if self._earth_gate_fn:
            try:
                gate = self._earth_gate_fn()
                if isinstance(gate, dict):
                    state.gate_open = gate.get("gate_open", True)
                    if not state.gate_open:
                        reasoning.append(f"Earth resonance gate CLOSED: {gate.get('reason', '?')}")
            except Exception:
                pass

        # --- 4. HNC Lambda Engine ---
        if self._lambda_engine:
            try:
                from aureon.core.aureon_lambda_engine import SubsystemReading

                # Feed cosmic data as subsystem readings
                readings = []
                readings.append(SubsystemReading(
                    "space_weather", state.cosmic_score, 0.8, state.kp_category))
                readings.append(SubsystemReading(
                    "schumann", state.earth_blessing, 0.9, f"Hz={state.schumann_hz:.2f}"))
                readings.append(SubsystemReading(
                    "earth_disturbance", 1.0 - state.earth_disturbance, 0.7, "inverse"))

                ls = self._lambda_engine.step(readings, volatility=state.earth_disturbance * 0.1)
                state.lambda_t = ls.lambda_t
                state.consciousness_psi = ls.consciousness_psi
                state.coherence_gamma = ls.coherence_gamma
                state.consciousness_level = ls.consciousness_level
                # Publish the cosmic/planetary field as a sub-field so the
                # whole-body consensus sees Dr Auris's Λ(t), not just the queens'.
                try:
                    from aureon.core.hnc_field import publish_subfield
                    publish_subfield("dr_auris_throne", ls)
                except Exception:  # noqa: BLE001
                    pass
            except Exception:
                pass

        # --- 5. Synthesize Advisory ---
        state.reasoning = reasoning
        state.advisory = self._compute_advisory(state)
        state.alignment_details = {
            "space_weather": state.cosmic_score,
            "schumann_blessing": state.earth_blessing,
            "earth_gate": 1.0 if state.gate_open else 0.0,
            "lambda_coherence": state.coherence_gamma,
            "consciousness": state.consciousness_psi,
        }

        return state

    def _compute_advisory(self, state: CosmicState) -> str:
        """Determine what to advise the Queen based on cosmic conditions."""
        # SLEEP: severe geomagnetic storm or consciousness too low
        if state.kp_index >= 7 or state.consciousness_psi < 0.1:
            return "SLEEP"

        # PROTECT: moderate storm, Earth gate closed, or high disturbance
        if state.kp_index >= 5 or not state.gate_open or state.earth_disturbance > 0.7:
            return "PROTECT"

        # TRADE: all systems green
        if (state.cosmic_score > 0.6
                and state.earth_blessing > 0.5
                and state.gate_open
                and state.coherence_gamma > 0.5):
            return "TRADE"

        # Default: OBSERVE
        return "OBSERVE"

    # ================================================================
    # PUBLISHING TO THOUGHTBUS
    # ================================================================

    def _publish_state(self, state: CosmicState) -> None:
        """Publish cosmic state to ThoughtBus for the Queen."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            cosmic_payload = {
                "kp_index": state.kp_index,
                "kp_category": state.kp_category,
                "solar_wind_speed": state.solar_wind_speed,
                "bz_component": state.bz_component,
                "solar_flares_24h": state.solar_flares_24h,
                "schumann_hz": state.schumann_hz,
                "schumann_coherence": state.schumann_coherence,
                "earth_disturbance": state.earth_disturbance,
                "earth_blessing": state.earth_blessing,
                "lambda_t": round(state.lambda_t, 4),
                "consciousness_psi": round(state.consciousness_psi, 4),
                "consciousness_level": state.consciousness_level,
                "coherence_gamma": round(state.coherence_gamma, 4),
                "cosmic_score": round(state.cosmic_score, 4),
                "gate_open": state.gate_open,
                "advisory": state.advisory,
                "reasoning": state.reasoning,
                "cycle": self._cycle_count,
            }
            self._thought_bus.publish(Thought(
                source="dr_auris_throne",
                topic="auris.throne.cosmic_state",
                payload=cosmic_payload,
            ))
            # Cross-process bridge: dr-auris runs in the organism process but
            # cognition subscribes to this topic in the operator process. Mirror
            # to a dedicated trace so the trace pump can re-fire it there.
            try:
                import time as _t

                from aureon.core.bus_trace import append_trace

                append_trace("auris_cosmic_state", {**cosmic_payload, "_ts": _t.time()}, cap=200)
            except Exception:  # noqa: BLE001
                pass

            # Also publish advisory as a separate topic for quick consumption
            self._thought_bus.publish(Thought(
                source="dr_auris_throne",
                topic="auris.throne.advisory",
                payload={
                    "advisory": state.advisory,
                    "cosmic_score": round(state.cosmic_score, 4),
                    "earth_blessing": round(state.earth_blessing, 4),
                    "gate_open": state.gate_open,
                    "coherence": round(state.coherence_gamma, 4),
                    "consciousness": state.consciousness_level,
                },
            ))
        except Exception:
            pass

    def _publish_alert(self, state: CosmicState) -> None:
        """Publish urgent cosmic alert."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            alerts = []
            if state.kp_index >= 5:
                alerts.append(f"GEOMAGNETIC STORM: Kp={state.kp_index}")
            if state.earth_disturbance > 0.7:
                alerts.append(f"EARTH FIELD DISTURBED: {state.earth_disturbance:.2f}")
            if state.bz_component < -10:
                alerts.append(f"SOUTHWARD Bz: {state.bz_component:.1f} nT (substorm imminent)")

            self._thought_bus.publish(Thought(
                source="dr_auris_throne",
                topic="auris.throne.alert",
                payload={
                    "alerts": alerts,
                    "severity": "CRITICAL" if state.kp_index >= 7 else "WARNING",
                    "advisory": state.advisory,
                    "kp_index": state.kp_index,
                    "earth_disturbance": state.earth_disturbance,
                },
            ))
        except Exception:
            pass

    # ================================================================
    # PUBLIC API
    # ================================================================

    def get_state(self) -> CosmicState:
        """Return the latest cosmic state."""
        return self._state

    def get_advisory(self) -> str:
        """Return current advisory: TRADE, OBSERVE, PROTECT, or SLEEP."""
        return self._state.advisory

    def is_gate_open(self) -> bool:
        """Return whether cosmic conditions support trading."""
        return self._state.gate_open and self._state.advisory in ("TRADE", "OBSERVE")

    def get_cosmic_score(self) -> float:
        """Return overall cosmic alignment score (0-1)."""
        return self._state.cosmic_score


# ============================================================================
# SINGLETON
# ============================================================================

_DR_AURIS: Optional[DrAurisThrone] = None


def get_dr_auris_throne() -> DrAurisThrone:
    """Get or create the global Dr. Auris Throne singleton."""
    global _DR_AURIS
    if _DR_AURIS is None:
        _DR_AURIS = DrAurisThrone()
    return _DR_AURIS
