"""HNC Live Field daemon — continuous Λ(t) computation from real data feeds.

Wires existing fetchers in ``aureon/`` onto an asyncio scheduler so the
Master Equation runs against live world data on a clock, instead of being
re-pulled per session. Each external source is polled at its native cadence;
their readings are normalised to the LambdaEngine's SubsystemReading shape
and fed to engine.step() in a fixed-rate compute loop.

Architecture (matches the 5-layer spec):

    Layer 1  — fetchers (existing repo APIs):
                * aureon.harmonic.aureon_schumann_resonance_bridge.SchumannResonanceBridge
                * aureon.data_feeds.aureon_space_weather_bridge.SpaceWeatherBridge
                * aureon.integrations.world_data.world_data_ingester.WorldDataIngester (.fetch_gdelt)
              Missing sources remain no-data and never create a field input.

    Layer 3  — kernel: aureon.core.aureon_lambda_engine.LambdaEngine,
              parameters loaded via aureon.core.hnc_params.

    Layer 4  — storage: piggybacks on LambdaEngine's auto-persist (which
              writes state/lambda_history.json every PERSIST_EVERY steps),
              plus an append-only JSONL trace at state/hnc_live_trace.jsonl.
              Parquet/SHA-chain (warm/cold storage) are out of scope here —
              the JSONL is the hot buffer.

    Layer 2 / 5 are out of scope of *this* module:
        Layer 2 (Schumann strip-diff render) remains a direct-source gap;
        the bridge emits no-data when direct or real-derived sources are down.
        Layer 5 (headless status command) is in ``aureon/status.py``.

The daemon is structured as one supervisor coroutine (``HNCLiveDaemon.run``)
that gathers source-pull tasks plus one fixed-cadence compute task. Each
source task owns its own retry/backoff. A source that fails its native
fetch leaves its last-good reading in place; the compute loop never blocks
waiting for any single source.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import logging
import math
import os
import signal
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from aureon.core.aureon_lambda_engine import (
    LambdaEngine,
    SubsystemReading,
    validate_history_receipt,
)
from aureon.core.hnc_params import HNCParams, apply_to_lambda_engine, load_params

logger = logging.getLogger(__name__)


# ─── Cadence config ────────────────────────────────────────────────
# Source-native intervals (seconds). Match the spec table.
SCHUMANN_INTERVAL = 300         # Tomsk JPEG updates ~5–10 min
SPACE_WEATHER_INTERVAL = 60     # USGS geomag every 1 min, NOAA Kp every 5
SPACE_WEATHER_PROVIDER_MAX_AGE_SECONDS = 600.0
GDELT_INTERVAL = 900            # GDELT 2.0 publishes every 15 min
BITFINEX_INTERVAL = 10          # ticker loop (when wired)
OMNI_INTERVAL = 3600            # OMNI hourly (when wired)
# Stage AF — added live data sources:
MACRO_INTERVAL = 60             # GlobalFinancialFeed has its own 60s cache
COINGECKO_INTERVAL = 300        # CoinGecko free tier ~50 calls/min
COMMUNITY_INTERVAL = 900        # Reddit + HN community sentiment
FRED_INTERVAL = 3600            # FRED economic releases are sparse
# Phase 16 — keyed science feeds (skip cleanly when the key is unset):
NOAA_CDO_INTERVAL = 3600        # NCEI Climate Data Online — slow daily records
USGS_WATER_INTERVAL = 1800      # USGS Water Data collections — slow feed
LOCAL_ACTION_INTERVAL = 60      # the organism's own local-machine moves
VOL_SENTINEL_INTERVAL = 5       # market volatility prediction — compute cadence
HARMONIC_SPECTRUM_INTERVAL = 15  # FFT-of-Λ(t) observer readback

# Compute cadence — how often the engine takes a step against the latest
# readings. The kernel is cheap (<1 ms/step) so 5 s gives the field high
# resolution without hammering the fetchers.
COMPUTE_INTERVAL = 5

# Backoff applied after a fetch raises.
BACKOFF_INITIAL = 30
BACKOFF_MAX = 600
SOURCE_CLOCK_FUTURE_SKEW_SECONDS = 5.0
REAL_SOURCE_TRUTH_STATUSES = frozenset({
    "live", "real_observed", "real_provider", "real_derived",
})


def _get_macro_snapshot_quietly(macro_feed: Any) -> Any:
    """Read the legacy macro feed without writing Unicode status art to stdio."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        return macro_feed.get_snapshot()


def _finite_timestamp(value: Any) -> Optional[float]:
    """Parse a provider timestamp without substituting the receipt clock."""
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


def _required_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _field_value(payload: Any, name: str) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(name)
    return getattr(payload, name, None)


@dataclass(frozen=True)
class SourceReceipt:
    """Complete immutable provenance for one accepted HNC input."""

    source_id: str
    source_timestamp: float
    received_at: float
    receipt_id: str
    receipt_type: str
    truth_status: str
    data_status: str = "live"
    generated_values: bool = False
    input_receipt_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_timestamp": self.source_timestamp,
            "received_at": self.received_at,
            "receipt_id": self.receipt_id,
            "receipt_type": self.receipt_type,
            "truth_status": self.truth_status,
            "data_status": self.data_status,
            "generated_values": self.generated_values,
            "input_receipt_ids": list(self.input_receipt_ids),
        }


@dataclass(frozen=True)
class SourceObservation:
    """A numeric Lambda input paired with its validated source receipt."""

    reading: SubsystemReading
    receipt: SourceReceipt


def _complete_source_observation(
    name: str,
    candidate: Any,
    *,
    now: float,
    max_age_s: float,
) -> Optional[SourceObservation]:
    """Return a validated observation or None; never invent provenance."""
    reading: Any
    if isinstance(candidate, SourceObservation):
        reading = candidate.reading
        raw_receipt: Any = candidate.receipt
    elif isinstance(candidate, Mapping):
        reading = candidate.get("reading")
        raw_receipt = candidate.get("receipt")
    else:
        return None
    if not isinstance(reading, SubsystemReading) or reading.name != name:
        return None
    try:
        value = float(reading.value)
        confidence = float(reading.confidence)
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(value)
        or not math.isfinite(confidence)
        or not 0.0 <= value <= 1.0
        or not 0.0 <= confidence <= 1.0
    ):
        return None

    source_id = _required_text(_field_value(raw_receipt, "source_id"))
    receipt_id = _required_text(_field_value(raw_receipt, "receipt_id"))
    receipt_type = _required_text(
        _field_value(raw_receipt, "receipt_type")
        or _field_value(raw_receipt, "provider_receipt_type")
    )
    truth_status = _required_text(_field_value(raw_receipt, "truth_status"))
    source_timestamp = _finite_timestamp(_field_value(raw_receipt, "source_timestamp"))
    received_at = _finite_timestamp(_field_value(raw_receipt, "received_at"))
    generated_values = _field_value(raw_receipt, "generated_values")
    data_status = _field_value(raw_receipt, "data_status")
    raw_links = _field_value(raw_receipt, "input_receipt_ids")
    if raw_links is None:
        links: Tuple[str, ...] = ()
    elif isinstance(raw_links, (list, tuple, set)):
        normalized_links = sorted({
            text for item in raw_links if (text := _required_text(item)) is not None
        })
        if len(normalized_links) != len(raw_links):
            return None
        links = tuple(normalized_links)
    else:
        return None
    if (
        source_id is None
        or receipt_id is None
        or receipt_type is None
        or truth_status not in REAL_SOURCE_TRUTH_STATUSES
        or data_status != "live"
        or generated_values is not False
        or source_timestamp is None
        or received_at is None
        or source_timestamp > now + SOURCE_CLOCK_FUTURE_SKEW_SECONDS
        or received_at > now + SOURCE_CLOCK_FUTURE_SKEW_SECONDS
        or received_at < source_timestamp - SOURCE_CLOCK_FUTURE_SKEW_SECONDS
        or now - source_timestamp > max_age_s
        or (truth_status == "real_derived" and not links)
    ):
        return None
    return SourceObservation(
        reading=SubsystemReading(
            name=reading.name,
            value=value,
            confidence=confidence,
            state=str(reading.state),
        ),
        receipt=SourceReceipt(
            source_id=source_id,
            source_timestamp=source_timestamp,
            received_at=received_at,
            receipt_id=receipt_id,
            receipt_type=receipt_type,
            truth_status=truth_status,
            data_status="live",
            generated_values=False,
            input_receipt_ids=links,
        ),
    )


def _source_payload(value: Any) -> Optional[Mapping[str, Any]]:
    """Expose source-owned receipt fields without inventing missing values."""
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


def _normalised_source_names(value: Any) -> Optional[Tuple[str, ...]]:
    if not isinstance(value, (list, tuple)):
        return None
    names = tuple(sorted({
        text for item in value if (text := _required_text(item)) is not None
    }))
    return names if names and len(names) == len(value) else None


def _provider_input_receipt_id(
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


def _make_derived_source_observation(
    name: str,
    reading: Optional[SubsystemReading],
    *,
    source_timestamp: Any,
    received_at: Any,
    input_receipt_ids: Tuple[str, ...],
    content: Mapping[str, Any],
) -> Optional[SourceObservation]:
    """Build a deterministic receipt from exact upstream IDs and content."""
    if reading is None or reading.name != name:
        return None
    provider_timestamp = _finite_timestamp(source_timestamp)
    receipt_timestamp = _finite_timestamp(received_at)
    normalized_ids = tuple(sorted({
        text
        for item in input_receipt_ids
        if (text := _required_text(item)) is not None
    }))
    try:
        value = float(reading.value)
        confidence = float(reading.confidence)
    except (TypeError, ValueError):
        return None
    if (
        provider_timestamp is None
        or receipt_timestamp is None
        or receipt_timestamp < provider_timestamp - SOURCE_CLOCK_FUTURE_SKEW_SECONDS
        or not normalized_ids
        or len(normalized_ids) != len(input_receipt_ids)
        or not math.isfinite(value)
        or not math.isfinite(confidence)
    ):
        return None
    material = {
        "name": name,
        "source_timestamp": provider_timestamp,
        "input_receipt_ids": list(normalized_ids),
        "reading": {
            "value": value,
            "confidence": confidence,
            "state": str(reading.state),
        },
        "content": content,
    }
    try:
        encoded = json.dumps(
            material,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    receipt_id = f"hnc.source.{name}:{hashlib.sha256(encoded).hexdigest()}"
    return SourceObservation(
        reading=reading,
        receipt=SourceReceipt(
            source_id=f"hnc.source.{name}",
            source_timestamp=provider_timestamp,
            received_at=receipt_timestamp,
            receipt_id=receipt_id,
            receipt_type="hnc_source_observation",
            truth_status="real_derived",
            data_status="live",
            generated_values=False,
            input_receipt_ids=normalized_ids,
        ),
    )


def _wrap_schumann_observation(
    raw_reading: Any,
    reading: Optional[SubsystemReading],
) -> Optional[SourceObservation]:
    """Bind a Schumann reading to its named provider and provider clock."""
    payload = _source_payload(raw_reading)
    if payload is None:
        return None
    active_sources = _normalised_source_names(payload.get("active_sources"))
    source_timestamp = _finite_timestamp(payload.get("source_timestamp"))
    received_at = _finite_timestamp(payload.get("timestamp"))
    truth_status = _required_text(payload.get("truth_status"))
    if (
        active_sources is None
        or source_timestamp is None
        or received_at is None
        or truth_status not in {"live", "real_derived"}
        or payload.get("generated_values") is not False
    ):
        return None
    input_ids = tuple(
        _provider_input_receipt_id("schumann", provider, source_timestamp)
        for provider in active_sources
    )
    return _make_derived_source_observation(
        "schumann",
        reading,
        source_timestamp=source_timestamp,
        received_at=received_at,
        input_receipt_ids=input_ids,
        content={
            "active_sources": list(active_sources),
            "provider_source_timestamp": source_timestamp,
            "provider_truth_status": truth_status,
        },
    )


def _wrap_space_weather_observation(
    raw_reading: Any,
    reading: Optional[SubsystemReading],
) -> Optional[SourceObservation]:
    """Bind a space-weather composite to every timestamped provider input."""
    payload = _source_payload(raw_reading)
    if payload is None:
        return None
    active_sources = _normalised_source_names(payload.get("active_sources"))
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
            or provider_timestamp > received_at + SOURCE_CLOCK_FUTURE_SKEW_SECONDS
            or received_at - provider_timestamp > SPACE_WEATHER_PROVIDER_MAX_AGE_SECONDS
        ):
            return None
        provider_timestamps[provider] = provider_timestamp
    required_core = {"NOAA-KP", "NOAA-SolarWind"}
    active_noaa_sources = {
        source for source in active_sources if source.startswith("NOAA-")
    }
    if (
        not required_core.issubset(provider_timestamps)
        or not active_noaa_sources.issubset(provider_timestamps)
    ):
        return None
    timestamp_rows = sorted(provider_timestamps.items())
    input_ids = tuple(
        _provider_input_receipt_id("space_weather", provider, provider_timestamp)
        for provider, provider_timestamp in timestamp_rows
    )
    return _make_derived_source_observation(
        "space_weather",
        reading,
        source_timestamp=max(provider_timestamps.values()),
        received_at=received_at,
        input_receipt_ids=input_ids,
        content={
            "active_sources": list(active_sources),
            "provider_source_timestamps": timestamp_rows,
        },
    )


def _wrap_world_data_observation(
    name: str,
    reading: Optional[SubsystemReading],
    raw_items: Any,
) -> Optional[SourceObservation]:
    """Accept only WorldDataItems carrying their complete provider receipt."""
    if isinstance(raw_items, (list, tuple)):
        items = tuple(raw_items)
    else:
        items = (raw_items,)
    if reading is None or not items or any(item is None for item in items):
        return None

    provider_rows: List[Dict[str, Any]] = []
    input_ids: List[str] = []
    source_timestamps: List[float] = []
    received_timestamps: List[float] = []
    for item in items:
        payload = _source_payload(item)
        if payload is None:
            return None
        source_id = _required_text(payload.get("source_id"))
        receipt_id = _required_text(payload.get("receipt_id"))
        source_timestamp = _finite_timestamp(payload.get("source_timestamp"))
        received_at = _finite_timestamp(payload.get("received_at"))
        truth_status = _required_text(payload.get("truth_status"))
        if (
            source_id is None
            or receipt_id is None
            or source_timestamp is None
            or received_at is None
            or received_at < source_timestamp - SOURCE_CLOCK_FUTURE_SKEW_SECONDS
            or truth_status not in {"live", "real_observed", "real_provider"}
            or payload.get("generated_values") is not False
            or payload.get("data_status") not in (None, "live")
            or any(
                payload.get(field_name, False) is not False
                for field_name in (
                    "action_enabled",
                    "accounting_enabled",
                    "learning_enabled",
                    "provider_eligible",
                )
            )
        ):
            return None
        input_ids.append(receipt_id)
        source_timestamps.append(source_timestamp)
        received_timestamps.append(received_at)
        provider_rows.append({
            "receipt_id": receipt_id,
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "truth_status": truth_status,
        })
    if len(set(input_ids)) != len(input_ids):
        return None
    return _make_derived_source_observation(
        name,
        reading,
        source_timestamp=min(source_timestamps),
        received_at=max(received_timestamps),
        input_receipt_ids=tuple(input_ids),
        content={"provider_receipts": sorted(
            provider_rows, key=lambda row: row["receipt_id"]
        )},
    )


@dataclass
class SourceState:
    """Per-source running state — cached reading, error count, last fetch ts.

    ``max_age_s`` is the honesty expiry: a cached reading older than this is
    excluded from the Λ compute step instead of lingering in Γ forever.
    """
    name: str
    interval_s: float
    last_reading: Optional[SubsystemReading] = None
    last_receipt: Optional[SourceReceipt] = None
    last_fetch_ts: float = 0.0
    error_count: int = 0
    backoff_s: float = BACKOFF_INITIAL
    max_age_s: float = 300.0

    def reading_for_compute(self, now: float) -> SubsystemReading | None:
        if self.last_reading is None or self.last_receipt is None:
            return None
        if (now - self.last_receipt.source_timestamp) > self.max_age_s:
            return None
        return self.last_reading


# ─── SubsystemReading mappers ─────────────────────────────────────
# Each external reading has its own shape. These functions normalise to
# the LambdaEngine input contract: name, value ∈ [0,1], confidence ∈ [0,1],
# state (free-form string).

def _map_schumann(reading) -> SubsystemReading | None:
    """SchumannReading → SubsystemReading.

    value      = amplitude (already 0..1)
    confidence = quality (Q-factor, already 0..1)
    state      = resonance_phase (stable/elevated/peak/disturbed)
    """
    if reading is None or getattr(reading, "truth_status", "") not in {"live", "real_derived"}:
        return None
    amplitude = getattr(reading, "amplitude", None)
    quality = getattr(reading, "quality", None)
    if amplitude is None or quality is None:
        return None
    return SubsystemReading(
        name="schumann",
        value=float(amplitude),
        confidence=float(quality),
        state=str(getattr(reading, "resonance_phase", "unknown")),
    )


def _map_space_weather(reading) -> SubsystemReading | None:
    """SpaceWeatherReading → SubsystemReading.

    The Kp index runs 0..9 (0 = quiet, 9 = severe storm). A *quiet*
    geomagnetic field is a high-coherence input to Λ, so we invert:
    value = 1 - Kp/9. Confidence is fixed because NOAA's feed is
    authoritative when present.
    """
    if reading is None or getattr(reading, "truth_status", "") != "live":
        return None
    raw_kp = getattr(reading, "kp_index", None)
    if raw_kp is None:
        return None
    kp = float(raw_kp)
    value = max(0.0, min(1.0, 1.0 - kp / 9.0))
    return SubsystemReading(
        name="space_weather",
        value=value,
        confidence=0.9,
        state=str(getattr(reading, "kp_category", "unknown")),
    )


def _map_gdelt(items: list) -> SubsystemReading | None:
    """GDELT article list → SubsystemReading.

    Phase 1 mapping: more articles in the last pull = higher world-event
    pressure. We tanh-saturate against 50 articles so the value lives in
    [0,1] and is monotonic in count.

    A real Phase 2 should compute the GDELT *tone* signal (already part
    of GDELT 2.0), but ``WorldDataIngester.fetch_gdelt`` doesn't expose
    tone yet — extending that is a separate change, not a daemon concern.
    """
    n = len(items) if items else 0
    if not n:
        return None
    import math
    value = math.tanh(n / 25.0)
    return SubsystemReading(
        name="gdelt",
        value=value,
        confidence=0.7,
        state=f"{n}_articles",
    )


def _map_macro(snapshot) -> SubsystemReading | None:
    """GlobalFinancialFeed.MacroSnapshot → SubsystemReading.

    Composite signal from the three most-watched macro indicators:
      vix_signal      : (100 - VIX) / 100  — high vol → low confidence
      fg_signal       : crypto_fear_greed / 100  — directly 0..1
      curve_signal    : 0 if yield curve inverted else 1

    Weighted blend: 0.4*vix + 0.4*fg + 0.2*curve. State carries the
    market_regime label (NORMAL / FEAR / GREED / PANIC / EUPHORIA).
    Confidence is fixed because the underlying Yahoo / FNG endpoints
    are authoritative when present.
    """
    if snapshot is None:
        return None
    raw_vix = getattr(snapshot, "vix", None)
    raw_fg = getattr(snapshot, "crypto_fear_greed", None)
    raw_curve = getattr(snapshot, "yield_curve_inversion", None)
    regime = getattr(snapshot, "market_regime", None)
    if raw_vix is None or raw_fg is None or raw_curve is None or not regime:
        return None
    vix = float(raw_vix)
    fg = float(raw_fg)
    curve_inv = bool(raw_curve)
    regime = str(regime)

    vix_signal = max(0.0, min(1.0, (100.0 - vix) / 100.0))
    fg_signal = max(0.0, min(1.0, fg / 100.0))
    curve_signal = 0.0 if curve_inv else 1.0
    value = 0.4 * vix_signal + 0.4 * fg_signal + 0.2 * curve_signal

    return SubsystemReading(
        name="macro_context",
        value=float(value),
        confidence=0.85,
        state=regime,
    )


def _map_coingecko(item) -> SubsystemReading | None:
    """CoinGecko WorldDataItem → SubsystemReading.

    Maps 24h percent change to a 0..1 directional value:
      -10%  → 0.0   (panic)
       0%   → 0.5   (flat)
      +10%  → 1.0   (rally)
      ±20%  → saturated at the bound
    State carries the human-readable summary (price + percent change).
    """
    if item is None:
        return None
    raw = getattr(item, "raw", None) or {}
    if raw.get("change_24h") is None or raw.get("price") is None:
        return None
    change_24h = float(raw["change_24h"])
    price = float(raw["price"])
    if price <= 0:
        return None
    value = max(0.0, min(1.0, 0.5 + change_24h / 20.0))
    return SubsystemReading(
        name="coingecko_btc",
        value=value,
        confidence=0.8,
        state=f"BTC ${price:,.0f} ({change_24h:+.2f}%)",
    )


# Crude bullish/bearish keyword lists for community sentiment scoring.
# Production-grade NLP belongs elsewhere; this is a directional
# heuristic over headlines only.
_COMM_BULL_KW = ("rally", "surge", "bull", "moon", "pump", "soar",
                 "breakout", "record high", "all-time", "ath", "boom")
_COMM_BEAR_KW = ("crash", "drop", "bear", "dump", "plunge", "tank",
                 "selloff", "collapse", "crater", "wipe out", "rout")


def _map_community(items_hn: list, items_reddit: list) -> SubsystemReading | None:
    """Reddit + Hacker News headlines → SubsystemReading.

    Crude keyword scoring per item: +1 (bullish kw match), -1 (bearish
    kw match), 0 (neither). Average → mapped from [-1, 1] to [0, 1].
    Confidence scales with the count of items processed and the share
    of items with any keyword hit (heavy-no-keyword pulls drop confidence).
    """
    items = (items_hn or []) + (items_reddit or [])
    if not items:
        return None
    scores = []
    hits = 0
    for it in items:
        title = (getattr(it, "title", "") or "").lower()
        s = 0
        if any(kw in title for kw in _COMM_BULL_KW):
            s += 1
        if any(kw in title for kw in _COMM_BEAR_KW):
            s -= 1
        scores.append(s)
        if s != 0:
            hits += 1
    avg = sum(scores) / len(scores)
    value = max(0.0, min(1.0, 0.5 + avg / 2.0))
    confidence = max(0.2, min(1.0, hits / max(len(items), 1)))
    return SubsystemReading(
        name="community_sentiment",
        value=float(value),
        confidence=float(confidence),
        state=f"{len(items)}_posts_{hits}_hits",
    )


def _map_fred(item) -> SubsystemReading | None:
    """FRED (UNRATE — US unemployment rate) → SubsystemReading.

    Lower unemployment ⇒ stronger economy ⇒ higher confidence. Linear
    map: 3% → 1.0, 8% → 0.0, clamped. The numeric value lives in
    item.raw["value"] as a string per fetch_fred's CSV parse.
    """
    if item is None:
        return None
    raw = getattr(item, "raw", None) or {}
    try:
        unrate = float(raw.get("value", "nan"))
    except (TypeError, ValueError):
        return None
    if unrate != unrate:  # NaN
        return None
    # Map 3..8% → 1..0
    value = max(0.0, min(1.0, (8.0 - unrate) / 5.0))
    return SubsystemReading(
        name="fred_unrate",
        value=float(value),
        confidence=0.9,  # FRED is authoritative
        state=f"UNRATE={unrate:.1f}%",
    )


def _map_noaa_climate(item) -> SubsystemReading | None:
    """NOAA NCEI Climate Data Online record → SubsystemReading.

    The daily climate record is an environmental-context input: a *present,
    authoritative* reading is a stable, high-confidence signal (value 0.75).
    A missing key/record degrades to a neutral, zero-confidence reading so the
    field simply ignores it. State carries the datatype + latest value.
    """
    # The current fetch is a catalogue/reachability read, not a climate
    # measurement. It remains observable but must not enter Λ as a value.
    return None


def _map_local_action(stats) -> SubsystemReading | None:
    """Recent local-machine action verdicts → SubsystemReading.

    This is the organism grounding its OWN moves back into the Master Formula:
    the coherence of what its hands are doing feeds Λ(t) like any external
    source. ``value`` = the recent approve ratio (a body acting within the
    conscience/β-stability island reads as coherent); ``confidence`` scales with
    how many moves we have seen. No activity → neutral, zero-confidence.
    """
    if not stats or not stats.get("count"):
        return None
    count = int(stats.get("count", 0))
    ratio = stats.get("approve_ratio")
    if ratio is None:
        return None
    value = float(ratio)
    import math
    confidence = min(0.9, math.tanh(count / 20.0))
    return SubsystemReading(
        name="local_action",
        value=max(0.0, min(1.0, value)),
        confidence=confidence,
        state=f"{count}_moves_{stats.get('veto_count', 0)}_vetoed",
    )


def _map_usgs_water(item) -> SubsystemReading | None:
    """USGS Water Data collections snapshot → SubsystemReading.

    Reachable, keyed water-data service = a stable environmental-context input.
    value scales gently with how many collections responded (tanh-saturated),
    so a richer response reads as marginally higher coherence. Absent → neutral.
    """
    # The current fetch is a collection catalogue/reachability read, not a
    # water measurement. It must not be converted into a coherence value.
    return None


def _map_volatility_sentinel(assessment) -> SubsystemReading | None:
    """VolatilityAssessment → SubsystemReading (the Fourier→Λ(t) seam).

    value = SAFETY = 1 − volatility_risk: predicted high volatility reads as a
    LOW subsystem value, which pulls Γ = 1−|σ/μ| down, which every
    reconcile_gamma order-path gate then takes as the tighter bound — b46
    tighten-only by construction, with zero edits at the ten gate sites.

    no_data → None, NEVER a neutral placeholder: Γ consumes reading VALUES
    regardless of confidence, so a substituted 0.5 would move the canonical
    field — fabrication by another name.
    """
    if assessment is None:
        return None
    risk = getattr(assessment, "volatility_risk", None)
    if getattr(assessment, "status", "no_data") != "ok" or risk is None:
        return None
    factors = [f.name for f in getattr(assessment, "factors", ())
               if getattr(f, "status", "") == "ok"]
    return SubsystemReading(
        name="volatility_sentinel",
        value=max(0.0, min(1.0, 1.0 - float(risk))),
        confidence=max(0.0, min(1.0, float(getattr(assessment, "confidence", 0.0)))),
        state=f"risk={float(risk):.2f};factors={','.join(factors) or 'none'}",
    )


def _map_harmonic_observer(observer) -> SubsystemReading | None:
    """HarmonicObserver → SubsystemReading (FFT of Λ(t) fed back into Λ(t)).

    value = the observer's rock-stability coherence score; state = its regime.
    WARMING (no data yet) → None. Confidence capped at 0.6 because this is a
    self-referential loop — the spectral view of the field must inform the
    field, never dominate it.
    """
    if observer is None:
        return None
    try:
        regime = str(observer.regime())
        if regime.upper() == "WARMING":
            return None
        score = float(observer.coherence_score())
    except Exception:
        return None
    return SubsystemReading(
        name="harmonic_spectrum",
        value=max(0.0, min(1.0, score)),
        confidence=0.6,
        state=regime,
    )


# ─── The daemon ───────────────────────────────────────────────────

class HNCLiveDaemon:
    """Asyncio-driven supervisor: one task per source + one compute loop.

    Usage:
        daemon = HNCLiveDaemon()
        asyncio.run(daemon.run(duration_s=None))   # run until SIGINT

    Caller wiring:
        - ``register_source(name, interval_s, fetch_coro, mapper)`` adds
          a custom source (Bitfinex, OMNI, etc.).
        - ``current_state`` returns the last LambdaState dict — used by
          the headless ``aureon.status`` entry point.
    """

    def __init__(self, params: Optional[HNCParams] = None,
                 trace_path: Optional[Path] = None,
                 attach_observer: bool = True,
                 observer=None,
                 state_path: Optional[Path] = None):
        """
        attach_observer: when True (default), construct a HarmonicObserver
            and feed it engine state on every compute step. The observer
            auto-claims the singleton (see aureon.observer.__init__) so
            the Queen sentience layer, the Kelly gate, and the
            PredictionBus all auto-pick it up — no extra wiring needed.
            Set False when you want the daemon's pure compute behaviour
            (e.g. running multiple daemons in one process).

        observer: pass a pre-constructed HarmonicObserver to use instead
            of the default. Useful for tests or for sharing one observer
            across multiple daemons. When None and attach_observer=True,
            a default observer is created.
        """
        self.params = apply_to_lambda_engine(params or load_params())
        self.engine = LambdaEngine(state_path=state_path)
        self._sources: Dict[str, SourceState] = {}
        self._fetchers: Dict[str, Callable[[], Awaitable[Any]]] = {}
        self._last_state_dict: Optional[dict] = None
        self._step_lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._trace_path = trace_path or (
            Path(__file__).resolve().parents[2] / "state" / "hnc_live_trace.jsonl"
        )
        self._trace_path.parent.mkdir(parents=True, exist_ok=True)
        self._observer = observer

        # Built-in sources — only wire if their bridges import cleanly.
        self._wire_default_sources()

        # Optional observer attach. Lazy-import + try/except so any
        # observer issue (missing module, missing numpy in sandbox) can
        # NEVER break daemon startup or the compute loop. The observer
        # is purely an output channel from this loop's perspective.
        if self._observer is None and attach_observer:
            try:
                from aureon.observer import HarmonicObserver
                self._observer = HarmonicObserver(publish_to_bus=True)
                logger.info("HNC daemon: HarmonicObserver attached (auto)")
            except Exception as exc:
                logger.warning("HNC daemon: HarmonicObserver attach skipped: %s", exc)
                self._observer = None
        elif self._observer is not None:
            logger.info("HNC daemon: HarmonicObserver attached (caller-provided)")

        # Stage AG: also construct WavePredictor + MomentumTracker
        # singletons. Their bus-predictor adapters (Stages Q + AC)
        # call get_wave_predictor() / get_momentum_tracker() at predict
        # time — if those return None, the predictors silently return
        # NEUTRAL conf=0 with reason 'wave_predictor_not_running' /
        # 'momentum_tracker_no_data'. The fix is to construct the
        # singletons HERE so they actually receive the live ticks the
        # daemon's compute loop + source loop produce.
        self._wave_predictor = None
        self._momentum_tracker = None
        if attach_observer:
            try:
                from aureon.observer.wave_predictor import WavePredictor
                self._wave_predictor = WavePredictor(observer=self._observer)
                logger.info("HNC daemon: WavePredictor attached (auto)")
            except Exception as exc:
                logger.warning("HNC daemon: WavePredictor attach skipped: %s", exc)
            try:
                from aureon.observer.momentum import MomentumTracker
                self._momentum_tracker = MomentumTracker()
                logger.info("HNC daemon: MomentumTracker attached (auto)")
            except Exception as exc:
                logger.warning("HNC daemon: MomentumTracker attach skipped: %s", exc)
        if self._observer is not None and "harmonic_spectrum" not in self._sources:
            async def fetch_harmonic_spectrum():
                return _map_harmonic_observer(self._observer)

            self.register_source(
                "harmonic_spectrum", HARMONIC_SPECTRUM_INTERVAL,
                fetch_harmonic_spectrum, max_age_s=180.0,
            )

    # ─── source registration ────────────────────────────────────

    def register_source(
        self,
        name: str,
        interval_s: float,
        fetcher: Callable[[], Awaitable[Any]],
        max_age_s: float | None = None,
    ) -> None:
        """Add a source. ``fetcher`` is an async callable that returns a
        SubsystemReading or None. The daemon handles cadence and retry.
        ``max_age_s`` expires the cached reading out of the Λ compute step
        when the source goes dark. The default is three source intervals,
        never an unbounded stale cache.
        """
        freshness_limit = float(max_age_s) if max_age_s is not None else max(60.0, float(interval_s) * 3.0)
        self._sources[name] = SourceState(
            name=name, interval_s=interval_s, max_age_s=freshness_limit)
        self._fetchers[name] = fetcher
        logger.info("HNC daemon: registered source %s @ %ss", name, interval_s)

    def _wire_default_sources(self) -> None:
        # Schumann
        try:
            from aureon.harmonic.aureon_schumann_resonance_bridge import get_schumann_bridge
            bridge = get_schumann_bridge()

            async def fetch_schumann():
                # SchumannResonanceBridge.get_live_data() is sync; run in thread.
                reading = await asyncio.to_thread(bridge.get_live_data)
                mapped = _map_schumann(reading) if reading else None
                return _wrap_schumann_observation(reading, mapped)

            self.register_source("schumann", SCHUMANN_INTERVAL, fetch_schumann)
        except Exception as exc:
            logger.warning("HNC daemon: schumann not wired (%s)", exc)

        # Space weather
        try:
            from aureon.data_feeds.aureon_space_weather_bridge import get_space_weather_bridge
            sw = get_space_weather_bridge()

            async def fetch_space_weather():
                reading = await asyncio.to_thread(sw.get_live_data)
                mapped = _map_space_weather(reading) if reading else None
                return _wrap_space_weather_observation(reading, mapped)

            self.register_source(
                "space_weather",
                SPACE_WEATHER_INTERVAL,
                fetch_space_weather,
                max_age_s=300.0,
            )
        except Exception as exc:
            logger.warning("HNC daemon: space_weather not wired (%s)", exc)

        # GDELT
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            ingester = WorldDataIngester()

            async def fetch_gdelt():
                items = await asyncio.to_thread(ingester.fetch_gdelt, "world", 25)
                return _wrap_world_data_observation(
                    "gdelt", _map_gdelt(items), items
                )

            self.register_source("gdelt", GDELT_INTERVAL, fetch_gdelt)
        except Exception as exc:
            logger.warning("HNC daemon: gdelt not wired (%s)", exc)

        # ─── Stage AF: macro context (VIX/DXY/fear-greed/forex) ──
        try:
            from aureon.data_feeds.global_financial_feed import GlobalFinancialFeed
            macro_feed = GlobalFinancialFeed()

            async def fetch_macro():
                snap = await asyncio.to_thread(_get_macro_snapshot_quietly, macro_feed)
                return _map_macro(snap) if snap is not None else None

            self.register_source("macro_context", MACRO_INTERVAL, fetch_macro)
        except Exception as exc:
            logger.warning("HNC daemon: macro_context not wired (%s)", exc)

        # ─── Stage AF: CoinGecko BTC market ───────────────────────
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            cg_ingester = WorldDataIngester()

            async def fetch_coingecko():
                item = await asyncio.to_thread(cg_ingester.fetch_coingecko, "bitcoin")
                mapped = _map_coingecko(item) if item is not None else None
                return _wrap_world_data_observation(
                    "coingecko_btc", mapped, item
                )

            self.register_source("coingecko_btc", COINGECKO_INTERVAL, fetch_coingecko)
        except Exception as exc:
            logger.warning("HNC daemon: coingecko_btc not wired (%s)", exc)

        # ─── Stage AF: HN + Reddit community sentiment ────────────
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            comm_ingester = WorldDataIngester()

            async def fetch_community():
                hn = await asyncio.to_thread(comm_ingester.fetch_hacker_news, 10)
                reddit = await asyncio.to_thread(
                    comm_ingester.fetch_reddit, "worldnews", 10
                )
                items = (hn or []) + (reddit or [])
                return _wrap_world_data_observation(
                    "community_sentiment", _map_community(hn, reddit), items
                )

            self.register_source(
                "community_sentiment", COMMUNITY_INTERVAL, fetch_community,
            )
        except Exception as exc:
            logger.warning("HNC daemon: community_sentiment not wired (%s)", exc)

        # ─── Stage AF: FRED unemployment rate ────────────────────
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            fred_ingester = WorldDataIngester()

            async def fetch_fred_unrate():
                item = await asyncio.to_thread(fred_ingester.fetch_fred, "UNRATE")
                mapped = _map_fred(item) if item is not None else None
                return _wrap_world_data_observation(
                    "fred_unrate", mapped, item
                )

            self.register_source("fred_unrate", FRED_INTERVAL, fetch_fred_unrate)
        except Exception as exc:
            logger.warning("HNC daemon: fred_unrate not wired (%s)", exc)

        # ─── Phase 16: NOAA NCEI climate (keyed — NOAA_API_KEY) ───
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            noaa_ingester = WorldDataIngester()

            async def fetch_noaa_climate():
                item = await asyncio.to_thread(noaa_ingester.fetch_noaa_climate)
                return _wrap_world_data_observation(
                    "noaa_climate", _map_noaa_climate(item), item
                )

            self.register_source("noaa_climate", NOAA_CDO_INTERVAL, fetch_noaa_climate)
        except Exception as exc:
            logger.warning("HNC daemon: noaa_climate not wired (%s)", exc)

        # ─── Phase 16: USGS Water Data (keyed — USGS_API_KEY) ─────
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            usgs_ingester = WorldDataIngester()

            async def fetch_usgs_water():
                item = await asyncio.to_thread(usgs_ingester.fetch_usgs_water)
                return _wrap_world_data_observation(
                    "usgs_water", _map_usgs_water(item), item
                )

            self.register_source("usgs_water", USGS_WATER_INTERVAL, fetch_usgs_water)
        except Exception as exc:
            logger.warning("HNC daemon: usgs_water not wired (%s)", exc)

        # ─── Phase 18: the organism's own local-machine moves ─────
        # Reads recent grounded-action verdicts off the bus (no operator import
        # cycle) so Λ(t) incorporates what the body is doing to its own machine.
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            _action_bus = get_thought_bus()

            from aureon.core.aureon_thought_bus import payload_of

            def _read_action_stats():
                # recall filters by topic, so verdicts aren't evicted by other
                # bus traffic before the source reads them.
                recent = _action_bus.recall("operator.action.verdict", limit=200) or []
                verdicts = [payload_of(t) for t in recent]
                if not verdicts:
                    # Cross-process fallback: verdicts are produced in the OPERATOR
                    # process, so this daemon's in-memory bus is empty. Read the
                    # dedicated trace the gate writes so Λ(t) senses real moves.
                    try:
                        from aureon.core.bus_trace import read_trace

                        verdicts = read_trace("local_action_verdict", limit=200)
                    except Exception:  # noqa: BLE001
                        verdicts = []
                if not verdicts:
                    return {"count": 0}
                approved = sum(1 for v in verdicts if v.get("approved"))
                vetoed = sum(1 for v in verdicts if v.get("verdict") in ("VETOED", "BLOCKED"))
                return {"count": len(verdicts), "approve_ratio": approved / len(verdicts),
                        "veto_count": vetoed}

            async def fetch_local_action():
                stats = await asyncio.to_thread(_read_action_stats)
                return _map_local_action(stats)

            self.register_source("local_action", LOCAL_ACTION_INTERVAL, fetch_local_action)
        except Exception as exc:
            logger.warning("HNC daemon: local_action not wired (%s)", exc)

        # ── volatility sentinel (market FFT surge + phase + QGITA + EWMA) ──
        # The Fourier→Λ(t) source: predicted high volatility lowers Γ, which
        # tightens every reconcile_gamma order-path gate. Prices come from the
        # same ws_cache the HNC live connector reads — real prices or no
        # ingest at all; a no_data assessment maps to None (never a
        # placeholder), and max_age_s expires the reading if the sentinel
        # goes dark so a stale risk cannot linger in Γ.
        try:
            from aureon.intelligence.volatility_sentinel import VolatilitySentinel

            _sentinel_symbols = [
                s.strip() for s in os.environ.get(
                    "HNC_SYMBOLS", "BTC/USD,ETH/USD,SOL/USD").split(",")
                if s.strip()
            ]
            _sentinel = VolatilitySentinel(symbols=_sentinel_symbols)
            self._volatility_sentinel = _sentinel

            def _load_ws_prices() -> dict:
                # Same cache + normalization as HncLiveConnector
                # (_load_prices_from_cache): 'prices' (binance) → BASE/USD,
                # 'ticker_cache' (coingecko) → PAIR. Missing/unreadable → {}.
                import json as _json
                from pathlib import Path as _Path
                path = _Path(os.environ.get(
                    "WS_PRICE_CACHE_PATH", "ws_cache/ws_prices.json"))
                if not path.exists():
                    return {}
                try:
                    payload = _json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    return {}
                out: dict = {}
                for base, price in (payload.get("prices") or {}).items():
                    try:
                        out[f"{base}/USD"] = float(price)
                    except Exception:
                        continue
                for pair, entry in (payload.get("ticker_cache") or {}).items():
                    try:
                        out[str(pair).upper()] = float(
                            (entry or {}).get("price", 0) or 0)
                    except Exception:
                        continue
                return out

            def _sentinel_step():
                prices = _load_ws_prices()
                for sym in _sentinel.symbols:
                    px = prices.get(sym)
                    if px and px > 0:
                        _sentinel.ingest_price(sym, px)
                assessment = _sentinel.assess_portfolio()
                # Publish even when no_data — the honest state is telemetry too.
                _sentinel.publish(assessment)
                return assessment

            async def fetch_volatility_sentinel():
                assessment = await asyncio.to_thread(_sentinel_step)
                return _map_volatility_sentinel(assessment)

            self.register_source(
                "volatility_sentinel", VOL_SENTINEL_INTERVAL,
                fetch_volatility_sentinel, max_age_s=120.0)
        except Exception as exc:
            logger.warning("HNC daemon: volatility_sentinel not wired (%s)", exc)

        # ── harmonic spectrum (FFT of Λ(t), the attached observer) ──
        # The observer already ingests every engine step; this closes its loop
        # back into Λ(t) as a bounded-confidence reading.
        try:
            if self._observer is not None:
                async def fetch_harmonic_spectrum():
                    return _map_harmonic_observer(self._observer)

                self.register_source(
                    "harmonic_spectrum", HARMONIC_SPECTRUM_INTERVAL,
                    fetch_harmonic_spectrum, max_age_s=180.0)
        except Exception as exc:
            logger.warning("HNC daemon: harmonic_spectrum not wired (%s)", exc)

    # ─── per-source pull loop ──────────────────────────────────

    async def _source_loop(self, name: str) -> None:
        st = self._sources[name]
        fetch = self._fetchers[name]
        while not self._stop.is_set():
            try:
                candidate = await fetch()
                now = time.time()
                observation = _complete_source_observation(
                    name,
                    candidate,
                    now=now,
                    max_age_s=st.max_age_s,
                )
                if observation is not None:
                    reading = observation.reading
                    st.last_reading = reading
                    st.last_receipt = observation.receipt
                    st.last_fetch_ts = observation.receipt.received_at
                    st.error_count = 0
                    st.backoff_s = BACKOFF_INITIAL
                    # Stage AC: feed the value into the momentum tracker
                    # so multi-horizon EMAs update for every source the
                    # daemon pulls. The tracker is a singleton and
                    # auto-wires onto PredictionBus; this is the data
                    # ingestion side.
                    try:
                        from aureon.observer.momentum import get_momentum_tracker
                        mt = get_momentum_tracker()
                        if mt is not None:
                            mt.ingest(
                                name,
                                float(reading.value),
                                observation.receipt.source_timestamp,
                            )
                    except Exception:
                        pass
                elif candidate is not None:
                    st.last_reading = None
                    st.last_receipt = None
                    logger.debug(
                        "HNC daemon: source %s returned an incomplete receipt",
                        name,
                    )
                wait = st.interval_s
            except Exception as exc:
                st.error_count += 1
                wait = min(st.backoff_s, BACKOFF_MAX)
                st.backoff_s = min(st.backoff_s * 2, BACKOFF_MAX)
                logger.warning(
                    "HNC daemon: source %s fetch failed (%s); backoff %ss",
                    name, exc, wait,
                )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=wait)
                return  # stop requested
            except asyncio.TimeoutError:
                pass

    # ─── compute loop ──────────────────────────────────────────

    def _no_data_envelope(self, received_at: float, reason: str) -> Dict[str, Any]:
        digest = hashlib.sha256(
            f"hnc_live_daemon|no_data|{reason}".encode("utf-8")
        ).hexdigest()[:24]
        return {
            "data_status": "no_data",
            "source": "hnc_live_daemon",
            "source_id": "aureon:hnc:live_daemon",
            "source_timestamp": None,
            "received_at": received_at,
            "ts": None,
            "receipt_id": f"hnc:no_data:{digest}",
            "receipt_type": "hnc_live_field",
            "provider_receipt_type": "hnc_live_field",
            "truth_status": "no_data",
            "generated_values": False,
            "input_receipt_ids": [],
            "reason": reason,
            "operational_eligible": False,
            "provider_eligible": False,
            "action_eligible": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "equation_inputs_complete": False,
            "action_gate_passed": False,
        }

    def _derived_envelope(
        self,
        state_dict: Dict[str, Any],
        readings: List[SubsystemReading],
        *,
        received_at: float,
        source_receipts: List[SourceReceipt],
        memory_receipt: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if (
            not readings
            or len(source_receipts) != len(readings)
            or any(not isinstance(receipt, SourceReceipt) for receipt in source_receipts)
        ):
            raise ValueError("exact source receipt snapshot required")
        validated_memory = validate_history_receipt(memory_receipt)
        if validated_memory is None:
            raise ValueError("complete Lambda history receipt required")
        provider_receipt_ids = sorted({
            receipt.receipt_id for receipt in source_receipts
        })
        if validated_memory["source_receipt_ids"] != provider_receipt_ids:
            raise ValueError("Lambda history receipt does not match current providers")
        state_step = state_dict.get("step")
        state_lambda = state_dict.get("lambda_t")
        state_psi = state_dict.get("consciousness_psi")
        if (
            isinstance(state_step, bool)
            or not isinstance(state_step, int)
            or isinstance(state_lambda, bool)
            or not isinstance(state_lambda, (int, float))
            or not math.isfinite(float(state_lambda))
            or isinstance(state_psi, bool)
            or not isinstance(state_psi, (int, float))
            or not math.isfinite(float(state_psi))
            or not validated_memory["history"]
            or not validated_memory["psi_history"]
            or validated_memory["step_count"] != state_step
            or validated_memory["history"][-1] != float(state_lambda)
            or validated_memory["psi_history"][-1] != float(state_psi)
        ):
            raise ValueError("Lambda history receipt does not match emitted state")
        memory_receipt_id = validated_memory["receipt_id"]
        memory_canonical_hash = validated_memory["canonical_hash"]
        memory_previous_receipt_id = validated_memory["previous_receipt_id"]
        input_receipt_ids = sorted({
            receipt.receipt_id
            for receipt in source_receipts
        } | {memory_receipt_id})
        source_timestamp = max(
            receipt.source_timestamp
            for receipt in source_receipts
        )
        fingerprint = {
            "input_receipt_ids": input_receipt_ids,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "step": state_dict.get("step"),
            "lambda_t": state_dict.get("lambda_t"),
            "coherence_gamma": state_dict.get("coherence_gamma"),
            "consciousness_psi": state_dict.get("consciousness_psi"),
            "symbolic_life_score": state_dict.get("symbolic_life_score"),
        }
        digest = hashlib.sha256(
            json.dumps(
                fingerprint,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()[:24]
        return {
            **state_dict,
            "data_status": "live",
            "source": "hnc_live_daemon",
            "source_id": "aureon:hnc:live_daemon",
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "ts": source_timestamp,
            "receipt_id": f"hnc:live_field:{digest}",
            "receipt_type": "hnc_live_field",
            "provider_receipt_type": "hnc_live_field",
            "truth_status": "real_derived",
            "generated_values": False,
            "input_receipt_ids": input_receipt_ids,
            "memory_receipt_id": memory_receipt_id,
            "memory_canonical_hash": memory_canonical_hash,
            "memory_previous_receipt_id": memory_previous_receipt_id,
            "freshness_status": "fresh",
            "operational_eligible": False,
            "provider_eligible": False,
            "action_eligible": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "equation_inputs_complete": True,
            "action_gate_passed": False,
            "action_gate_reason": "route_specific_market_link_required",
        }

    def _publish_pulse(self, envelope: Dict[str, Any]) -> None:
        try:
            from aureon.core.aureon_thought_bus import Thought, get_thought_bus

            keys = {
                "data_status", "source", "source_id", "source_timestamp",
                "received_at", "ts", "receipt_id", "receipt_type",
                "provider_receipt_type", "truth_status", "generated_values",
                "input_receipt_ids", "memory_receipt_id",
                "memory_canonical_hash", "memory_previous_receipt_id",
                "reason", "freshness_status",
                "operational_eligible", "provider_eligible",
                "action_eligible", "actionable", "accounting_eligible",
                "learning_eligible", "eligible_for_action",
                "eligible_for_accounting", "eligible_for_learning",
                "equation_inputs_complete", "action_gate_passed",
                "action_gate_reason", "symbolic_life_score",
                "coherence_gamma", "consciousness_psi",
                "consciousness_level", "lambda_t", "step", "source_count",
            }
            payload = {
                key: value for key, value in envelope.items() if key in keys
            }
            get_thought_bus().publish(Thought(
                source="hnc_live_daemon",
                topic="symbolic.life.pulse",
                payload=payload,
            ))
        except Exception as exc:
            logger.debug("symbolic.life.pulse publish failed: %s", exc)

    def _snapshot_source_observations(
        self,
        received_at: float,
    ) -> List[SourceObservation]:
        """Freeze the exact reading/receipt pairs used by one heartbeat."""
        observations: List[SourceObservation] = []
        for source_state in self._sources.values():
            reading = source_state.reading_for_compute(received_at)
            receipt = source_state.last_receipt
            if reading is None or receipt is None:
                continue
            observations.append(SourceObservation(
                reading=SubsystemReading(
                    name=reading.name,
                    value=float(reading.value),
                    confidence=float(reading.confidence),
                    state=str(reading.state),
                ),
                receipt=receipt,
            ))
        return observations

    async def _compute_transaction(
        self,
        received_at: float,
    ) -> Tuple[Optional[Any], Dict[str, Any], List[SubsystemReading]]:
        observations = self._snapshot_source_observations(received_at)
        if not observations:
            return (
                None,
                self._no_data_envelope(
                    received_at,
                    "complete_fresh_real_source_receipt_required",
                ),
                [],
            )

        readings = [observation.reading for observation in observations]
        source_receipts = [observation.receipt for observation in observations]
        source_receipt_ids = sorted({
            receipt.receipt_id for receipt in source_receipts
        })
        async with self._step_lock:
            checkpoint = self.engine.checkpoint_history()
            try:
                state = self.engine.step(
                    readings,
                    source_receipt_ids=source_receipt_ids,
                    auto_persist=False,
                )
            except Exception as exc:
                self.engine.rollback_history(checkpoint)
                logger.warning("HNC Lambda step rolled back: %s", exc)
                return (
                    None,
                    self._no_data_envelope(
                        received_at,
                        "lambda_step_failed_rollback",
                    ),
                    [],
                )
            memory_receipt = self.engine.save_history(
                source_receipt_ids=source_receipt_ids
            )
            if memory_receipt is None:
                self.engine.rollback_history(checkpoint)
                logger.warning(
                    "HNC Lambda history commit rolled back: %s",
                    self.engine.last_history_commit_error,
                )
                return (
                    None,
                    self._no_data_envelope(
                        received_at,
                        "lambda_history_commit_failed_rollback",
                    ),
                    [],
                )

        envelope = self._derived_envelope(
            state.to_dict(),
            readings,
            received_at=received_at,
            source_receipts=source_receipts,
            memory_receipt=memory_receipt,
        )
        envelope["source_count"] = len(readings)
        return state, envelope, readings

    async def _compute_loop(self) -> None:
        while not self._stop.is_set():
            _now = time.time()
            state, envelope, readings = await self._compute_transaction(_now)
            self._last_state_dict = envelope
            self._append_trace(envelope, readings)
            self._publish_pulse(envelope)
            if state is None:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=COMPUTE_INTERVAL)
                    return
                except asyncio.TimeoutError:
                    continue

            # Feed the engine state into the attached observer. Wrapped
            # so any observer error (numpy missing in sandbox, scipy
            # crash on a degenerate window, etc.) cannot interrupt the
            # compute loop — the daemon's job is to keep ticking.
            if self._observer is not None:
                try:
                    self._observer.ingest_state(state)
                    # The observer's local field joins the whole-body consensus
                    # as a sub-field (throttled inside publish_field; no-op
                    # before it has data).
                    self._observer.publish_field()
                except Exception as exc:
                    logger.debug("observer.ingest_state failed: %s", exc)

            # Stage AG: also feed the wave predictor on every compute
            # step. The predictor's confidence depends on having a
            # window of LambdaState samples to fit a slope through;
            # without ingest_state calls here it stays at 0 forever.
            if self._wave_predictor is not None:
                try:
                    self._wave_predictor.ingest_state(state)
                except Exception as exc:
                    logger.debug("wave_predictor.ingest_state failed: %s", exc)

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=COMPUTE_INTERVAL)
                return
            except asyncio.TimeoutError:
                pass

    # ─── trace I/O ─────────────────────────────────────────────

    def _append_trace(self, state_dict: dict, readings: List[SubsystemReading]) -> None:
        """Append-only JSONL trace — the Phase-1 hot buffer.

        One line per kernel step. Cheap, recoverable, easy to feed back
        into a fitter. The LambdaEngine separately auto-persists its
        history deque to state/lambda_history.json.
        """
        try:
            provenance_keys = (
                "data_status", "source", "source_id", "source_timestamp",
                "received_at", "ts", "receipt_id", "receipt_type",
                "provider_receipt_type", "truth_status", "generated_values",
                "input_receipt_ids", "memory_receipt_id",
                "memory_canonical_hash", "memory_previous_receipt_id",
                "reason", "freshness_status",
                "operational_eligible", "provider_eligible",
                "action_eligible", "actionable", "accounting_eligible",
                "learning_eligible", "eligible_for_action",
                "eligible_for_accounting", "eligible_for_learning",
                "equation_inputs_complete", "action_gate_passed",
                "action_gate_reason",
            )
            row = {
                key: state_dict.get(key)
                for key in provenance_keys
                if key in state_dict
            }
            if state_dict.get("data_status") == "live":
                row.update({
                    "step": state_dict.get("step"),
                    "lambda_t": state_dict.get("lambda_t"),
                    "consciousness_psi": state_dict.get("consciousness_psi"),
                    "consciousness_level": state_dict.get("consciousness_level"),
                    "coherence_gamma": state_dict.get("coherence_gamma"),
                    "symbolic_life_score": state_dict.get("symbolic_life_score"),
                    "source_count": state_dict.get("source_count"),
                    "sources": {
                        r.name: {
                            "value": r.value,
                            "confidence": r.confidence,
                            "state": r.state,
                            **receipt.to_dict(),
                            "freshness_ttl_s": self._sources[r.name].max_age_s,
                        }
                        for r in readings
                        if (receipt := self._sources[r.name].last_receipt)
                        is not None
                    },
                })
            with open(self._trace_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        except Exception as exc:
            logger.debug("trace append failed: %s", exc)

    # ─── public API ────────────────────────────────────────────

    @property
    def current_state(self) -> Optional[dict]:
        """Last LambdaState as a dict, or None if the compute loop hasn't
        ticked yet. Used by aureon.status for headless inspection."""
        return self._last_state_dict

    @property
    def source_status(self) -> Dict[str, dict]:
        """Per-source last-fetch metadata for the status command."""
        now = time.time()
        return {
            name: {
                "interval_s": st.interval_s,
                "last_fetch_ts": st.last_fetch_ts,
                "lag_s": (now - st.last_fetch_ts) if st.last_fetch_ts else None,
                "error_count": st.error_count,
                "has_reading": st.last_reading is not None,
                "receipt_id": (
                    st.last_receipt.receipt_id if st.last_receipt else None
                ),
                "source_timestamp": (
                    st.last_receipt.source_timestamp if st.last_receipt else None
                ),
                "received_at": (
                    st.last_receipt.received_at if st.last_receipt else None
                ),
            }
            for name, st in self._sources.items()
        }

    async def run(self, duration_s: Optional[float] = None) -> None:
        """Start the daemon. ``duration_s=None`` runs until SIGINT/SIGTERM."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._stop.set)
            except (NotImplementedError, RuntimeError):
                pass  # Windows / non-main-thread

        tasks = [
            asyncio.create_task(self._source_loop(name), name=f"src:{name}")
            for name in self._sources
        ]
        tasks.append(asyncio.create_task(self._compute_loop(), name="compute"))

        if duration_s is not None:
            asyncio.create_task(self._stop_after(duration_s))

        logger.info(
            "HNC live daemon started (sources=%s, params=%s)",
            list(self._sources), self.params,
        )
        await self._stop.wait()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        # Every accepted heartbeat is committed before publication, so shutdown
        # never creates an unreceipted extra memory revision.
        logger.info("HNC live daemon stopped.")

    async def _stop_after(self, duration_s: float) -> None:
        await asyncio.sleep(duration_s)
        self._stop.set()


# ─── module main — the console entry point (aureon-hnc / python -m) ──────────

def main() -> None:
    """Run the HNC live daemon. The ``aureon-hnc`` console-script + ``python -m
    aureon.core.hnc_live_daemon`` entry — mirrors ``organism_daemon.main()``."""
    logging.basicConfig(
        level=os.environ.get("AUREON_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Bring every credential into the environment before the sources wire — the
    # daemon otherwise loads nothing, so NASA_API_KEY (DONKI enrichment) and the
    # NOAA/USGS keys would be invisible to the fetchers. Presence-only self-check.
    try:
        from aureon.core.aureon_env import bootstrap_credentials

        _boot = bootstrap_credentials()
        _keys = " ".join(f"{k.split('_')[0]}={'on' if v else 'off'}" for k, v in _boot["present"].items())
        logger.info("HNC daemon credentials: %s", _keys)
    except Exception as exc:  # noqa: BLE001 - never block the daemon on env setup
        logger.warning("HNC daemon: credential bootstrap skipped (%s)", exc)
    duration = float(os.environ.get("AUREON_HNC_DAEMON_DURATION", "0")) or None
    asyncio.run(HNCLiveDaemon().run(duration_s=duration))


if __name__ == "__main__":
    main()
