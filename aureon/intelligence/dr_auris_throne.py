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

import hashlib
import json
import logging
import math
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Sacred constants
PHI = 1.618033988749895
PHI_SQUARED = PHI ** 2  # 2.618 -- the chain from Sumer to Now
SCHUMANN_HZ = 7.83
LOVE_HZ = 528.0
CROWN_HZ = 963.0
RECEIPT_MAX_AGE_SECONDS = 300.0
RECEIPT_FUTURE_SKEW_SECONDS = 5.0
SPACE_WEATHER_PROVIDER_MAX_AGE_SECONDS = 600.0
REAL_TRUTH_STATUSES = frozenset({
    "live", "real_observed", "real_provider", "real_derived",
})
EVIDENCE_ONLY_FIELDS = (
    "operational_eligible",
    "provider_eligible",
    "action_eligible",
    "actionable",
    "accounting_eligible",
    "learning_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "action_gate_passed",
)


def _required_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _finite_timestamp(value: Any) -> Optional[float]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                value = parsed.timestamp()
            except (TypeError, ValueError, OverflowError):
                try:
                    parsed = parsedate_to_datetime(text)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    value = parsed.timestamp()
                except (TypeError, ValueError, OverflowError):
                    return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def _finite_number(
    value: Any,
    *,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def _complete_receipt(
    raw: Any,
    *,
    now: float,
    max_age_s: float,
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, Mapping):
        return None
    source_id = _required_text(raw.get("source_id"))
    receipt_id = _required_text(raw.get("receipt_id"))
    receipt_type = _required_text(
        raw.get("receipt_type") or raw.get("provider_receipt_type")
    )
    truth_status = _required_text(raw.get("truth_status"))
    source_timestamp = _finite_timestamp(raw.get("source_timestamp"))
    received_at = _finite_timestamp(raw.get("received_at"))
    raw_links = raw.get("input_receipt_ids")
    if raw_links is None:
        links: List[str] = []
    elif isinstance(raw_links, (list, tuple, set)):
        links = sorted({
            text for item in raw_links if (text := _required_text(item)) is not None
        })
        if len(links) != len(raw_links):
            return None
    else:
        return None
    if (
        source_id is None
        or receipt_id is None
        or receipt_type is None
        or truth_status not in REAL_TRUTH_STATUSES
        or raw.get("data_status") != "live"
        or raw.get("generated_values") is not False
        or any(
            raw.get(field_name) is not False
            for field_name in EVIDENCE_ONLY_FIELDS
        )
        or source_timestamp is None
        or received_at is None
        or source_timestamp > now + RECEIPT_FUTURE_SKEW_SECONDS
        or received_at > now + RECEIPT_FUTURE_SKEW_SECONDS
        or received_at < source_timestamp - RECEIPT_FUTURE_SKEW_SECONDS
        or now - source_timestamp > max_age_s
        or (truth_status == "real_derived" and not links)
    ):
        return None
    return {
        **raw,
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": receipt_id,
        "receipt_type": receipt_type,
        "provider_receipt_type": receipt_type,
        "truth_status": truth_status,
        "generated_values": False,
        "input_receipt_ids": links,
    }


def _source_payload(value: Any) -> Optional[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        return value
    to_dict = getattr(value, "to_dict", None)
    if not callable(to_dict):
        return None
    try:
        payload = to_dict()
    except Exception:
        return None
    return payload if isinstance(payload, Mapping) else None


def _source_names(value: Any) -> Optional[List[str]]:
    if not isinstance(value, (list, tuple)):
        return None
    names = sorted({
        text for item in value if (text := _required_text(item)) is not None
    })
    return names if names and len(names) == len(value) else None


def _provider_receipt_id(
    namespace: str,
    provider_id: str,
    source_timestamp: float,
) -> str:
    material = {
        "namespace": namespace,
        "provider_id": provider_id,
        "source_timestamp": source_timestamp,
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"{namespace}.provider:{digest}"


def _derived_evidence_receipt(
    *,
    source_id: str,
    receipt_prefix: str,
    receipt_type: str,
    source_timestamp: float,
    received_at: float,
    input_receipt_ids: List[str],
    fields: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    normalized_ids = sorted({
        text
        for item in input_receipt_ids
        if (text := _required_text(item)) is not None
    })
    if not normalized_ids or len(normalized_ids) != len(input_receipt_ids):
        return None
    fingerprint = {
        "source_id": source_id,
        "receipt_type": receipt_type,
        "source_timestamp": source_timestamp,
        "input_receipt_ids": normalized_ids,
        "fields": fields,
    }
    try:
        encoded = json.dumps(
            fingerprint,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return {
        "data_status": "live",
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": f"{receipt_prefix}:{digest}",
        "receipt_type": receipt_type,
        "provider_receipt_type": receipt_type,
        "truth_status": "real_derived",
        "generated_values": False,
        "input_receipt_ids": normalized_ids,
        **fields,
        "operational_eligible": False,
        "provider_eligible": False,
        "action_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "action_gate_passed": False,
    }


def _space_weather_evidence_receipt(
    raw_reading: Any,
    cosmic_score_value: Any,
    *,
    now: float,
    max_age_s: float,
) -> Optional[Dict[str, Any]]:
    payload = _source_payload(raw_reading)
    if payload is None:
        return None
    active_sources = _source_names(payload.get("active_sources"))
    raw_timestamps = payload.get("source_timestamps")
    received_at = _finite_timestamp(payload.get("timestamp"))
    if (
        active_sources is None
        or not isinstance(raw_timestamps, Mapping)
        or received_at is None
        or payload.get("truth_status") != "live"
        or payload.get("generated_values") is not False
    ):
        return None
    provider_timestamps: Dict[str, float] = {}
    for raw_provider, raw_timestamp in raw_timestamps.items():
        provider = _required_text(raw_provider)
        provider_timestamp = _finite_timestamp(raw_timestamp)
        if (
            provider is None
            or provider not in active_sources
            or provider_timestamp is None
            or provider_timestamp > received_at + RECEIPT_FUTURE_SKEW_SECONDS
            or now - provider_timestamp > SPACE_WEATHER_PROVIDER_MAX_AGE_SECONDS
        ):
            return None
        provider_timestamps[provider] = provider_timestamp
    active_noaa_sources = {
        source for source in active_sources if source.startswith("NOAA-")
    }
    if (
        not {"NOAA-KP", "NOAA-SolarWind"}.issubset(provider_timestamps)
        or not active_noaa_sources.issubset(provider_timestamps)
    ):
        return None
    metrics = {
        "kp_index": _finite_number(
            payload.get("kp_index"), minimum=0.0, maximum=9.0
        ),
        "kp_category": _required_text(payload.get("kp_category")),
        "solar_wind_speed": _finite_number(
            payload.get("solar_wind_speed"), minimum=0.0
        ),
        "bz_component": _finite_number(payload.get("bz_component")),
        "cosmic_score": _finite_number(
            cosmic_score_value, minimum=0.0, maximum=1.0
        ),
    }
    raw_solar_flares = payload.get("solar_flares_24h")
    solar_flares = (
        None
        if raw_solar_flares is None
        else _finite_number(raw_solar_flares, minimum=0.0)
    )
    if raw_solar_flares is not None and solar_flares is None:
        return None
    if any(value is None for value in metrics.values()):
        return None
    if solar_flares is not None and not solar_flares.is_integer():
        return None
    solar_flares_24h = int(solar_flares) if solar_flares is not None else None
    timestamp_rows = sorted(provider_timestamps.items())
    receipt = _derived_evidence_receipt(
        source_id="aureon:planetary:space_weather",
        receipt_prefix="space_weather",
        receipt_type="planetary_space_weather_evidence",
        source_timestamp=max(provider_timestamps.values()),
        received_at=received_at,
        input_receipt_ids=[
            _provider_receipt_id("space_weather", provider, provider_timestamp)
            for provider, provider_timestamp in timestamp_rows
        ],
        fields={
            **metrics,
            "solar_flares_24h": solar_flares_24h,
            "solar_flares_24h_available": solar_flares_24h is not None,
            "geomagnetic_storm_3day": str(
                payload.get("geomagnetic_storm_3day") or ""
            ),
            "active_sources": active_sources,
            "provider_source_timestamps": timestamp_rows,
        },
    )
    return _complete_receipt(receipt, now=now, max_age_s=max_age_s)


def _schumann_evidence_receipt(
    raw_reading: Any,
    *,
    now: float,
    max_age_s: float,
) -> Optional[Dict[str, Any]]:
    payload = _source_payload(raw_reading)
    if payload is None:
        return None
    active_sources = _source_names(payload.get("active_sources"))
    source_timestamp = _finite_timestamp(payload.get("source_timestamp"))
    received_at = _finite_timestamp(payload.get("timestamp"))
    metrics = {
        "fundamental_hz": _finite_number(
            payload.get("fundamental_hz"), minimum=0.000001
        ),
        "coherence": _finite_number(
            payload.get("quality"), minimum=0.0, maximum=1.0
        ),
        "amplitude": _finite_number(
            payload.get("amplitude"), minimum=0.0, maximum=1.0
        ),
        "earth_disturbance_level": _finite_number(
            payload.get("earth_disturbance_level"),
            minimum=0.0,
            maximum=1.0,
        ),
    }
    if (
        active_sources is None
        or source_timestamp is None
        or received_at is None
        or payload.get("truth_status") not in {"live", "real_derived"}
        or payload.get("generated_values") is not False
        or any(value is None for value in metrics.values())
    ):
        return None
    receipt = _derived_evidence_receipt(
        source_id="aureon:planetary:schumann",
        receipt_prefix="schumann",
        receipt_type="planetary_schumann_evidence",
        source_timestamp=source_timestamp,
        received_at=received_at,
        input_receipt_ids=[
            _provider_receipt_id("schumann", provider, source_timestamp)
            for provider in active_sources
        ],
        fields={
            **metrics,
            "active_sources": active_sources,
            "provider_truth_status": payload.get("truth_status"),
        },
    )
    return _complete_receipt(receipt, now=now, max_age_s=max_age_s)


def _earth_blessing_evidence_receipt(
    schumann_receipt: Mapping[str, Any],
    raw_blessing: Any,
    *,
    now: float,
    max_age_s: float,
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_blessing, (list, tuple)) or len(raw_blessing) != 2:
        return None
    blessing = _finite_number(
        raw_blessing[0], minimum=0.0, maximum=1.0
    )
    message = _required_text(raw_blessing[1])
    if blessing is None or message is None:
        return None
    receipt = _derived_evidence_receipt(
        source_id="aureon:planetary:earth_blessing",
        receipt_prefix="earth_blessing",
        receipt_type="planetary_earth_blessing_evidence",
        source_timestamp=schumann_receipt["source_timestamp"],
        received_at=now,
        input_receipt_ids=[schumann_receipt["receipt_id"]],
        fields={"earth_blessing": blessing, "reason": message},
    )
    return _complete_receipt(receipt, now=now, max_age_s=max_age_s)


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
    solar_flares_24h: Optional[int] = None
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
    gate_open: bool = False           # Opens only on complete linked evidence
    advisory: str = "SLEEP"           # TRADE, OBSERVE, PROTECT, SLEEP
    reasoning: List[str] = field(default_factory=list)
    timestamp: float = 0.0

    # Provenance. Every numeric field above has a plausible default (7.83 Hz, coherence
    # 0.5, cosmic_score 0.5), so a state assembled with no source connected looked exactly
    # like a quiet, measured sky. These say which sources actually answered this cycle, so
    # a consumer can tell a reading from a default — and ``data_available`` is False when
    # nothing answered at all.
    sources_live: List[str] = field(default_factory=list)
    sources_unavailable: List[str] = field(default_factory=list)
    data_status: str = "no_data"
    source_id: str = "aureon:auris:throne"
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    receipt_type: str = "auris_cosmic_state"
    truth_status: str = "no_data"
    generated_values: bool = False
    input_receipt_ids: List[str] = field(default_factory=list)
    hnc_receipt_id: Optional[str] = None
    planetary_receipt_ids: List[str] = field(default_factory=list)
    source_receipts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    operational_eligible: bool = False
    provider_eligible: bool = False
    action_eligible: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    eligible_for_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False

    @property
    def data_available(self) -> bool:
        """True only for a complete linked HNC plus planetary receipt chain."""
        return self.data_status == "live" and bool(self.receipt_id)


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

    def __init__(
        self,
        cycle_interval: float = 10.0,
        *,
        hnc_receipt_fn: Optional[Callable[[], Any]] = None,
        clock: Callable[[], float] = time.time,
        receipt_max_age_s: float = RECEIPT_MAX_AGE_SECONDS,
        space_weather_bridge: Any = None,
        schumann_bridge: Any = None,
        earth_engine: Any = None,
        lambda_engine: Any = None,
    ):
        self._cycle_interval = cycle_interval
        self._clock = clock
        self._receipt_max_age_s = float(receipt_max_age_s)
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
        self._hnc_receipt_fn = hnc_receipt_fn or self._read_latest_hnc_receipt

        # Lambda Engine (HNC Master Formula)
        self._lambda_engine = lambda_engine
        if self._lambda_engine is None:
            try:
                from aureon.core.aureon_lambda_engine import LambdaEngine
                self._lambda_engine = LambdaEngine()
            except Exception:
                pass

        self._space_weather_bridge = space_weather_bridge
        if self._space_weather_bridge is None:
            try:
                from aureon.data_feeds.aureon_space_weather_bridge import (
                    get_space_weather_bridge,
                )
                self._space_weather_bridge = get_space_weather_bridge()
            except Exception:
                pass

        self._schumann_bridge = schumann_bridge
        if self._schumann_bridge is None:
            try:
                from aureon.harmonic.aureon_schumann_resonance_bridge import (
                    get_schumann_bridge,
                )
                self._schumann_bridge = get_schumann_bridge()
            except Exception:
                pass

        self._earth_engine = earth_engine
        if self._earth_engine is None:
            try:
                from aureon.harmonic.earth_resonance_engine import get_earth_engine
                self._earth_engine = get_earth_engine()
            except Exception:
                pass

        self._planetary_receipt_bundle_fn = self._build_default_planetary_receipts
        self._space_weather_fn = None
        self._schumann_fn = None
        self._schumann_reading_fn = None
        self._earth_gate_fn = None

        logger.info("[DR. AURIS THRONE] Planetary Harmonic Intelligence Engine initialized")

    def _read_latest_hnc_receipt(self) -> Optional[Dict[str, Any]]:
        """Read one local canonical pulse; never fetch or synthesize a source.

        ThoughtBus is the in-process fast path. The dedicated HNC JSONL trace
        is the cross-process source of truth used when the HNC daemon and Auris
        throne run as separate operating-system processes.
        """
        if self._thought_bus is not None and hasattr(self._thought_bus, "recall"):
            try:
                from aureon.core.aureon_thought_bus import payload_of

                pulses = self._thought_bus.recall("symbolic.life.pulse", limit=1) or []
                if pulses:
                    payload = payload_of(pulses[-1])
                    if isinstance(payload, Mapping):
                        return dict(payload)
            except Exception:
                pass

        try:
            from aureon.core.bus_trace import read_trace_latest

            payload = read_trace_latest("hnc_live_trace")
            return dict(payload) if isinstance(payload, Mapping) else None
        except Exception:
            return None

    def _build_default_planetary_receipts(
        self,
        now: float,
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch each raw provider once and build one linked evidence bundle."""
        receipts: Dict[str, Dict[str, Any]] = {}
        if self._space_weather_bridge is not None:
            try:
                space_reading = self._space_weather_bridge.get_live_data()
                cosmic_score = self._space_weather_bridge.get_cosmic_score(
                    space_reading
                )
                space_receipt = _space_weather_evidence_receipt(
                    space_reading,
                    cosmic_score,
                    now=now,
                    max_age_s=self._receipt_max_age_s,
                )
                if space_receipt is not None:
                    receipts["space_weather"] = space_receipt
            except Exception:
                pass

        if self._schumann_bridge is None:
            return receipts
        try:
            schumann_reading = self._schumann_bridge.get_live_data()
            schumann_receipt = _schumann_evidence_receipt(
                schumann_reading,
                now=now,
                max_age_s=self._receipt_max_age_s,
            )
        except Exception:
            schumann_reading = None
            schumann_receipt = None
        if schumann_receipt is None:
            return receipts
        receipts["schumann"] = schumann_receipt

        try:
            blessing_result = self._schumann_bridge.get_earth_blessing(
                schumann_reading
            )
            blessing_receipt = _earth_blessing_evidence_receipt(
                schumann_receipt,
                blessing_result,
                now=now,
                max_age_s=self._receipt_max_age_s,
            )
            if blessing_receipt is not None:
                receipts["earth_blessing"] = blessing_receipt
        except Exception:
            pass

        if self._earth_engine is not None:
            try:
                earth_state = self._earth_engine.update_from_schumann_receipt(
                    schumann_receipt,
                    received_at=now,
                    max_age_s=self._receipt_max_age_s,
                )
                gate_receipt = None
                if earth_state is not None:
                    gate_receipt = self._earth_engine.get_trading_gate_receipt(
                        schumann_receipt,
                        received_at=now,
                        max_age_s=self._receipt_max_age_s,
                    )
                gate_receipt = _complete_receipt(
                    gate_receipt,
                    now=now,
                    max_age_s=self._receipt_max_age_s,
                )
                if gate_receipt is not None:
                    receipts["earth_gate"] = gate_receipt
            except Exception:
                pass
        return receipts

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
        now = self._clock()
        state = CosmicState(timestamp=now, received_at=now)
        reasoning = []
        receipts: Dict[str, Dict[str, Any]] = {}
        planetary_bundle: Dict[str, Any] = {}
        bundle_fn = getattr(self, "_planetary_receipt_bundle_fn", None)
        if callable(bundle_fn):
            try:
                raw_bundle = bundle_fn(now)
                if isinstance(raw_bundle, Mapping):
                    planetary_bundle = dict(raw_bundle)
            except Exception:
                planetary_bundle = {}

        def planetary_input(name: str, legacy_supplier: Any) -> Any:
            if name in planetary_bundle:
                return planetary_bundle[name]
            return legacy_supplier() if callable(legacy_supplier) else None

        try:
            raw_hnc = self._hnc_receipt_fn() if self._hnc_receipt_fn else None
        except Exception:
            raw_hnc = None
        hnc = _complete_receipt(
            raw_hnc,
            now=now,
            max_age_s=self._receipt_max_age_s,
        )
        if hnc is not None:
            hnc_metrics = {
                "symbolic_life_score": _finite_number(
                    hnc.get("symbolic_life_score"), minimum=0.0, maximum=1.0
                ),
                "coherence_gamma": _finite_number(
                    hnc.get("coherence_gamma"), minimum=0.0, maximum=1.0
                ),
                "consciousness_psi": _finite_number(
                    hnc.get("consciousness_psi"), minimum=0.0, maximum=1.0
                ),
                "lambda_t": _finite_number(hnc.get("lambda_t")),
            }
            evidence_flags = (
                "operational_eligible", "provider_eligible",
                "action_eligible", "accounting_eligible", "learning_eligible",
                "eligible_for_action", "eligible_for_accounting",
                "eligible_for_learning",
            )
            if (
                not hnc["source_id"].startswith("aureon:hnc:")
                or hnc["receipt_type"] != "hnc_live_field"
                or any(value is None for value in hnc_metrics.values())
                or any(hnc.get(flag) is not False for flag in evidence_flags)
            ):
                hnc = None
            else:
                hnc.update(hnc_metrics)
        if hnc is None:
            state.sources_unavailable.append("hnc")
        else:
            receipts["hnc"] = hnc

        # --- 1. Space Weather (NOAA/NASA) ---
        space_weather_fn = getattr(self, "_space_weather_fn", None)
        if "space_weather" not in planetary_bundle and not callable(space_weather_fn):
            state.sources_unavailable.append("space_weather")
        else:
            try:
                sw = _complete_receipt(
                    planetary_input("space_weather", space_weather_fn),
                    now=now,
                    max_age_s=self._receipt_max_age_s,
                )
                if sw is None:
                    raise ValueError("complete_space_weather_receipt_required")
                kp_index = _finite_number(
                    sw.get("kp_index"), minimum=0.0, maximum=9.0
                )
                kp_category = _required_text(sw.get("kp_category"))
                solar_wind_speed = _finite_number(
                    sw.get("solar_wind_speed"), minimum=0.0
                )
                bz_component = _finite_number(sw.get("bz_component"))
                raw_solar_flares = sw.get("solar_flares_24h")
                solar_flares = (
                    None
                    if raw_solar_flares is None
                    else _finite_number(raw_solar_flares, minimum=0.0)
                )
                if raw_solar_flares is not None and solar_flares is None:
                    raise ValueError(
                        "finite_optional_solar_flare_count_required"
                    )
                cosmic_score = _finite_number(
                    sw.get("cosmic_score"), minimum=0.0, maximum=1.0
                )
                if (
                    kp_index is None
                    or kp_category is None
                    or solar_wind_speed is None
                    or bz_component is None
                    or (
                        solar_flares is not None
                        and not solar_flares.is_integer()
                    )
                    or cosmic_score is None
                ):
                    raise ValueError("complete_space_weather_metrics_required")
                state.kp_index = kp_index
                state.kp_category = kp_category
                state.solar_wind_speed = solar_wind_speed
                state.bz_component = bz_component
                state.solar_flares_24h = (
                    int(solar_flares) if solar_flares is not None else None
                )
                state.geomagnetic_forecast = str(
                    sw.get("geomagnetic_storm_3day") or ""
                )
                state.cosmic_score = cosmic_score
                receipts["space_weather"] = sw
                state.sources_live.append("space_weather")

                if state.kp_index >= 5:
                    reasoning.append(f"Geomagnetic storm: Kp={state.kp_index} ({state.kp_category})")
                if state.bz_component < -5:
                    reasoning.append(f"Southward Bz ({state.bz_component:.1f} nT) — substorm risk")
                if (
                    state.solar_flares_24h is not None
                    and state.solar_flares_24h > 0
                ):
                    reasoning.append(f"{state.solar_flares_24h} solar flares in 24h")
            except Exception as e:
                logger.debug(f"Space weather unavailable: {e}")
                state.sources_unavailable.append("space_weather")

        # --- 2. Schumann Resonance ---
        schumann_fn = getattr(self, "_schumann_fn", None)
        if "earth_blessing" not in planetary_bundle and not callable(schumann_fn):
            state.sources_unavailable.append("earth_blessing")
        else:
            try:
                blessing_receipt = _complete_receipt(
                    planetary_input("earth_blessing", schumann_fn),
                    now=now,
                    max_age_s=self._receipt_max_age_s,
                )
                if blessing_receipt is None:
                    raise ValueError("complete_earth_blessing_receipt_required")
                blessing = _finite_number(
                    blessing_receipt.get(
                        "earth_blessing", blessing_receipt.get("blessing")
                    ),
                    minimum=0.0,
                    maximum=1.0,
                )
                if blessing is None:
                    raise ValueError("finite_earth_blessing_required")
                state.earth_blessing = blessing
                receipts["earth_blessing"] = blessing_receipt
                state.sources_live.append("earth_blessing")
                if blessing < 0.4:
                    reasoning.append(f"Earth field disturbed (blessing={blessing:.2f})")
                elif blessing > 0.7:
                    reasoning.append(f"Earth field coherent (blessing={blessing:.2f})")
            except Exception:
                state.sources_unavailable.append("earth_blessing")

        schumann_reading_fn = getattr(self, "_schumann_reading_fn", None)
        if "schumann" not in planetary_bundle and not callable(schumann_reading_fn):
            state.sources_unavailable.append("schumann")
        else:
            try:
                reading = _complete_receipt(
                    planetary_input("schumann", schumann_reading_fn),
                    now=now,
                    max_age_s=self._receipt_max_age_s,
                )
                if reading is None:
                    raise ValueError("complete_schumann_receipt_required")
                fundamental_hz = _finite_number(
                    reading.get("fundamental_hz"), minimum=0.000001
                )
                coherence = _finite_number(
                    reading.get("coherence", reading.get("quality")),
                    minimum=0.0,
                    maximum=1.0,
                )
                amplitude = _finite_number(
                    reading.get("amplitude"), minimum=0.0, maximum=1.0
                )
                disturbance = _finite_number(
                    reading.get("earth_disturbance_level"),
                    minimum=0.0,
                    maximum=1.0,
                )
                if None in (
                    fundamental_hz, coherence, amplitude, disturbance
                ):
                    raise ValueError("complete_schumann_metrics_required")
                state.schumann_hz = fundamental_hz
                state.schumann_coherence = coherence
                state.schumann_amplitude = amplitude
                state.earth_disturbance = disturbance
                receipts["schumann"] = reading
                state.sources_live.append("schumann")
            except Exception:
                state.sources_unavailable.append("schumann")

        # --- 3. Earth Resonance Gate ---
        earth_gate_fn = getattr(self, "_earth_gate_fn", None)
        if "earth_gate" not in planetary_bundle and not callable(earth_gate_fn):
            state.sources_unavailable.append("earth_gate")
        else:
            try:
                gate = _complete_receipt(
                    planetary_input("earth_gate", earth_gate_fn),
                    now=now,
                    max_age_s=self._receipt_max_age_s,
                )
                if gate is None or not isinstance(gate.get("gate_open"), bool):
                    raise ValueError("complete_earth_gate_receipt_required")
                state.gate_open = gate["gate_open"]
                receipts["earth_gate"] = gate
                state.sources_live.append("earth_gate")
                if not state.gate_open:
                    reasoning.append(f"Earth resonance gate CLOSED: {gate.get('reason', '?')}")
            except Exception:
                state.sources_unavailable.append("earth_gate")

        schumann_receipt = receipts.get("schumann")
        if schumann_receipt is not None:
            exact_schumann_link = [schumann_receipt["receipt_id"]]
            for linked_name in ("earth_blessing", "earth_gate"):
                linked_receipt = receipts.get(linked_name)
                if (
                    linked_receipt is not None
                    and linked_receipt["input_receipt_ids"] != exact_schumann_link
                ):
                    receipts.pop(linked_name, None)
                    state.sources_live = [
                        name for name in state.sources_live
                        if name != linked_name
                    ]
                    state.sources_unavailable.append(linked_name)

        required_planetary = {
            "space_weather", "earth_blessing", "schumann", "earth_gate",
        }
        missing = sorted(required_planetary - set(receipts))
        if hnc is None:
            missing.insert(0, "hnc")
        if self._lambda_engine is None:
            missing.append("lambda_engine")
        state.sources_unavailable = sorted(set(
            state.sources_unavailable + missing
        ))
        state.source_receipts = {
            name: {
                "source_id": receipt["source_id"],
                "source_timestamp": receipt["source_timestamp"],
                "received_at": receipt["received_at"],
                "receipt_id": receipt["receipt_id"],
                "receipt_type": receipt["receipt_type"],
                "truth_status": receipt["truth_status"],
                "generated_values": False,
                "input_receipt_ids": list(receipt["input_receipt_ids"]),
                "operational_eligible": False,
                "provider_eligible": False,
                "action_eligible": False,
                "actionable": False,
                "accounting_eligible": False,
                "learning_eligible": False,
                "eligible_for_action": False,
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
                "action_gate_passed": False,
            }
            for name, receipt in receipts.items()
        }
        if missing:
            state.gate_open = False
            state.advisory = "SLEEP"
            state.reasoning = [
                "complete fresh linked HNC and planetary receipts required",
                f"missing_or_invalid={','.join(missing)}",
            ]
            partial_ids = sorted({
                receipt["receipt_id"] for receipt in receipts.values()
            })
            state.input_receipt_ids = partial_ids
            digest = hashlib.sha256(
                json.dumps(
                    {
                        "status": "no_data",
                        "missing": missing,
                        "input_receipt_ids": partial_ids,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()[:24]
            state.receipt_id = f"auris:no_data:{digest}"
            return state

        state.sources_live = sorted(required_planetary | {"hnc"})

        # --- 4. HNC Lambda Engine ---
        # Only run on real readings. The engine was fed cosmic_score / earth_blessing /
        # earth_disturbance unconditionally, so with no source connected it computed a Λ(t)
        # out of the dataclass defaults (0.5, 0.5, 0.0) and published it as the cosmic
        # sub-field — a fabricated contribution to the organism's shared HNC consensus.
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

            _cfr = SubsystemReading(
                "hnc_canonical_field",
                hnc["symbolic_life_score"],
                0.9,
                str(hnc.get("consciousness_level") or "live"),
            )
            readings.append(_cfr)

            ls = self._lambda_engine.step(readings, volatility=state.earth_disturbance * 0.1)
            state.lambda_t = ls.lambda_t
            state.consciousness_psi = ls.consciousness_psi
            state.coherence_gamma = ls.coherence_gamma
            state.consciousness_level = ls.consciousness_level
        except Exception:
            state.gate_open = False
            state.advisory = "SLEEP"
            state.sources_unavailable.append("lambda_engine")
            state.reasoning = ["validated inputs could not produce an Auris receipt"]
            digest = hashlib.sha256(
                b"auris|no_data|lambda_engine_failed"
            ).hexdigest()[:24]
            state.receipt_id = f"auris:no_data:{digest}"
            return state

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
        planetary_receipt_ids = sorted(
            receipts[name]["receipt_id"] for name in required_planetary
        )
        input_receipt_ids = sorted({
            receipt["receipt_id"]
            for receipt in receipts.values()
        } | {
            linked_id
            for receipt in receipts.values()
            for linked_id in receipt["input_receipt_ids"]
        })
        state.source_timestamp = max(
            receipt["source_timestamp"] for receipt in receipts.values()
        )
        state.hnc_receipt_id = hnc["receipt_id"]
        state.planetary_receipt_ids = planetary_receipt_ids
        state.input_receipt_ids = input_receipt_ids
        fingerprint = {
            "input_receipt_ids": input_receipt_ids,
            "lambda_t": state.lambda_t,
            "coherence_gamma": state.coherence_gamma,
            "consciousness_psi": state.consciousness_psi,
            "cosmic_score": state.cosmic_score,
            "earth_blessing": state.earth_blessing,
            "gate_open": state.gate_open,
            "advisory": state.advisory,
        }
        digest = hashlib.sha256(
            json.dumps(
                fingerprint,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()[:24]
        state.receipt_id = f"auris:cosmic_state:{digest}"
        state.data_status = "live"
        state.truth_status = "real_derived"

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

    def _evidence_payload(self, state: CosmicState) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "data_status": state.data_status,
            "source_id": state.source_id,
            "source_timestamp": state.source_timestamp,
            "received_at": state.received_at,
            "receipt_id": state.receipt_id,
            "receipt_type": state.receipt_type,
            "provider_receipt_type": state.receipt_type,
            "truth_status": state.truth_status,
            "generated_values": False,
            "data_available": state.data_available,
            "input_receipt_ids": list(state.input_receipt_ids),
            "hnc_receipt_id": state.hnc_receipt_id,
            "planetary_receipt_ids": list(state.planetary_receipt_ids),
            "operational_eligible": False,
            "provider_eligible": False,
            "action_eligible": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "equation_inputs_complete": state.data_available,
            "action_gate_passed": False,
            "action_gate_reason": "route_specific_market_link_required",
            "gate_open": state.gate_open if state.data_available else False,
            "advisory": state.advisory if state.data_available else "SLEEP",
            "reasoning": list(state.reasoning),
            "sources_live": list(state.sources_live),
            "sources_unavailable": list(state.sources_unavailable),
            "source_receipts": dict(state.source_receipts),
        }
        if state.data_available:
            payload.update({
                "kp_index": state.kp_index,
                "kp_category": state.kp_category,
                "solar_wind_speed": state.solar_wind_speed,
                "bz_component": state.bz_component,
                "solar_flares_24h": state.solar_flares_24h,
                "solar_flares_24h_available": (
                    state.solar_flares_24h is not None
                ),
                "schumann_hz": state.schumann_hz,
                "schumann_coherence": state.schumann_coherence,
                "earth_disturbance": state.earth_disturbance,
                "earth_blessing": state.earth_blessing,
                # These five values are receipt-causal. Preserve their exact
                # finite values so the serialized envelope validates against
                # the receipt minted in _analyze_cosmos; presentation layers
                # may round only after validation.
                "lambda_t": state.lambda_t,
                "consciousness_psi": state.consciousness_psi,
                "consciousness_level": state.consciousness_level,
                "coherence_gamma": state.coherence_gamma,
                "cosmic_score": state.cosmic_score,
                "cycle": self._cycle_count,
            })
        return payload

    def _publish_state(self, state: CosmicState) -> None:
        """Publish cosmic state to ThoughtBus for the Queen."""
        cosmic_payload = self._evidence_payload(state)
        # The trace is the cross-process evidence bridge and must not depend on
        # this process having an in-memory ThoughtBus. A valid Auris receipt
        # otherwise disappears whenever the producer runs as a one-shot or a
        # separate daemon.
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(
                "auris_cosmic_state",
                {**cosmic_payload, "_ts": state.received_at},
                cap=200,
            )
        except Exception:  # noqa: BLE001
            pass

        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought

            self._thought_bus.publish(Thought(
                source="dr_auris_throne",
                topic="auris.throne.cosmic_state",
                payload=cosmic_payload,
            ))

            # Also publish advisory as a separate topic for quick consumption
            self._thought_bus.publish(Thought(
                source="dr_auris_throne",
                topic="auris.throne.advisory",
                payload={
                    "data_status": state.data_status,
                    "source_id": state.source_id,
                    "source_timestamp": state.source_timestamp,
                    "received_at": state.received_at,
                    "receipt_id": state.receipt_id,
                    "receipt_type": state.receipt_type,
                    "provider_receipt_type": state.receipt_type,
                    "truth_status": state.truth_status,
                    "generated_values": False,
                    "input_receipt_ids": list(state.input_receipt_ids),
                    "hnc_receipt_id": state.hnc_receipt_id,
                    "operational_eligible": False,
                    "provider_eligible": False,
                    "action_eligible": False,
                    "actionable": False,
                    "accounting_eligible": False,
                    "learning_eligible": False,
                    "eligible_for_action": False,
                    "eligible_for_accounting": False,
                    "eligible_for_learning": False,
                    "advisory": state.advisory,
                    "gate_open": state.gate_open if state.data_available else False,
                    **({
                        "cosmic_score": round(state.cosmic_score, 4),
                        "earth_blessing": round(state.earth_blessing, 4),
                        "coherence": round(state.coherence_gamma, 4),
                        "consciousness": state.consciousness_level,
                    } if state.data_available else {}),
                },
            ))
        except Exception:
            pass

    def _publish_alert(self, state: CosmicState) -> None:
        """Publish urgent cosmic alert."""
        if self._thought_bus is None or not state.data_available:
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
                    "source_id": state.source_id,
                    "source_timestamp": state.source_timestamp,
                    "received_at": state.received_at,
                    "receipt_id": state.receipt_id,
                    "receipt_type": state.receipt_type,
                    "truth_status": state.truth_status,
                    "generated_values": False,
                    "input_receipt_ids": list(state.input_receipt_ids),
                    "action_eligible": False,
                    "accounting_eligible": False,
                    "learning_eligible": False,
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

    def refresh_once(self) -> CosmicState:
        """Gather, publish, and return one complete evidence cycle.

        This is the bounded composition-root entry point for release preflights
        and one-shot diagnostics.  It uses the same analysis and publication
        path as the background thread but does not start or retain a worker.
        """
        self._cycle_count += 1
        state = self._analyze_cosmos()
        self._state = state
        self._publish_state(state)
        if state.kp_index >= 5 or state.earth_disturbance > 0.7 or state.bz_component < -10:
            self._publish_alert(state)
        return state

    def get_state(self) -> CosmicState:
        """Return the latest cosmic state."""
        return self._state

    def get_advisory(self) -> str:
        """Return current advisory: TRADE, OBSERVE, PROTECT, or SLEEP."""
        return self._state.advisory

    def is_gate_open(self) -> bool:
        """Return whether cosmic conditions support trading."""
        return (
            self._state.data_available
            and self._state.gate_open
            and self._state.advisory in ("TRADE", "OBSERVE")
        )

    def get_cosmic_score(self) -> Optional[float]:
        """Return a measured score, or None while the receipt chain is dark."""
        return self._state.cosmic_score if self._state.data_available else None


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
