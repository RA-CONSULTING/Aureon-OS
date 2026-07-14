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
              Plug-in slots (NotImplemented unless the user supplies):
                * Bitfinex BTC ticks (no fetcher in repo today)
                * NASA OMNI hourly  (no fetcher in repo today)

    Layer 3  — kernel: aureon.core.aureon_lambda_engine.LambdaEngine,
              parameters loaded via aureon.core.hnc_params.

    Layer 4  — storage: piggybacks on LambdaEngine's auto-persist (which
              writes state/lambda_history.json every PERSIST_EVERY steps),
              plus an append-only JSONL trace at state/hnc_live_trace.jsonl.
              Parquet/SHA-chain (warm/cold storage) are out of scope here —
              the JSONL is the hot buffer.

    Layer 2 / 5 are out of scope of *this* module:
        Layer 2 (Schumann strip-diff render) is the single biggest gap and
        deserves its own module; today the SchumannResonanceBridge falls
        back to simulation when its sources are down. The daemon will
        happily consume real readings the moment the bridge starts
        returning them.
        Layer 5 (headless status command) is in ``aureon/status.py``.

The daemon is structured as one supervisor coroutine (``HNCLiveDaemon.run``)
that gathers source-pull tasks plus one fixed-cadence compute task. Each
source task owns its own retry/backoff. A source that fails its native
fetch leaves its last-good reading in place; the compute loop never blocks
waiting for any single source.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
from aureon.core.hnc_params import HNCParams, apply_to_lambda_engine, load_params

logger = logging.getLogger(__name__)


# ─── Cadence config ────────────────────────────────────────────────
# Source-native intervals (seconds). Match the spec table.
SCHUMANN_INTERVAL = 300         # Tomsk JPEG updates ~5–10 min
SPACE_WEATHER_INTERVAL = 60     # USGS geomag every 1 min, NOAA Kp every 5
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

# Compute cadence — how often the engine takes a step against the latest
# readings. The kernel is cheap (<1 ms/step) so 5 s gives the field high
# resolution without hammering the fetchers.
COMPUTE_INTERVAL = 5

# Backoff applied after a fetch raises.
BACKOFF_INITIAL = 30
BACKOFF_MAX = 600


@dataclass
class SourceState:
    """Per-source running state — cached reading, error count, last fetch ts."""
    name: str
    interval_s: float
    last_reading: Optional[SubsystemReading] = None
    last_fetch_ts: float = 0.0
    error_count: int = 0
    backoff_s: float = BACKOFF_INITIAL


# ─── SubsystemReading mappers ─────────────────────────────────────
# Each external reading has its own shape. These functions normalise to
# the LambdaEngine input contract: name, value ∈ [0,1], confidence ∈ [0,1],
# state (free-form string).

def _map_schumann(reading) -> SubsystemReading:
    """SchumannReading → SubsystemReading.

    value      = amplitude (already 0..1)
    confidence = quality (Q-factor, already 0..1)
    state      = resonance_phase (stable/elevated/peak/disturbed)
    """
    return SubsystemReading(
        name="schumann",
        value=float(getattr(reading, "amplitude", 0.5) or 0.5),
        confidence=float(getattr(reading, "quality", 0.5) or 0.5),
        state=str(getattr(reading, "resonance_phase", "unknown")),
    )


def _map_space_weather(reading) -> SubsystemReading:
    """SpaceWeatherReading → SubsystemReading.

    The Kp index runs 0..9 (0 = quiet, 9 = severe storm). A *quiet*
    geomagnetic field is a high-coherence input to Λ, so we invert:
    value = 1 - Kp/9. Confidence is fixed because NOAA's feed is
    authoritative when present.
    """
    kp = float(getattr(reading, "kp_index", 3.0) or 3.0)
    value = max(0.0, min(1.0, 1.0 - kp / 9.0))
    return SubsystemReading(
        name="space_weather",
        value=value,
        confidence=0.9,
        state=str(getattr(reading, "kp_category", "unknown")),
    )


def _map_gdelt(items: list) -> SubsystemReading:
    """GDELT article list → SubsystemReading.

    Phase 1 mapping: more articles in the last pull = higher world-event
    pressure. We tanh-saturate against 50 articles so the value lives in
    [0,1] and is monotonic in count.

    A real Phase 2 should compute the GDELT *tone* signal (already part
    of GDELT 2.0), but ``WorldDataIngester.fetch_gdelt`` doesn't expose
    tone yet — extending that is a separate change, not a daemon concern.
    """
    n = len(items) if items else 0
    import math
    value = math.tanh(n / 25.0)
    return SubsystemReading(
        name="gdelt",
        value=value,
        confidence=0.7 if n else 0.3,
        state=f"{n}_articles",
    )


def _map_macro(snapshot) -> SubsystemReading:
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
        return SubsystemReading(
            name="macro_context", value=0.5, confidence=0.0, state="unavailable",
        )
    vix = float(getattr(snapshot, "vix", 20.0) or 20.0)
    fg = float(getattr(snapshot, "crypto_fear_greed", 50) or 50)
    curve_inv = bool(getattr(snapshot, "yield_curve_inversion", False))
    regime = str(getattr(snapshot, "market_regime", "NORMAL") or "NORMAL")

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


def _map_coingecko(item) -> SubsystemReading:
    """CoinGecko WorldDataItem → SubsystemReading.

    Maps 24h percent change to a 0..1 directional value:
      -10%  → 0.0   (panic)
       0%   → 0.5   (flat)
      +10%  → 1.0   (rally)
      ±20%  → saturated at the bound
    State carries the human-readable summary (price + percent change).
    """
    if item is None:
        return SubsystemReading(
            name="coingecko_btc", value=0.5, confidence=0.0, state="unavailable",
        )
    raw = getattr(item, "raw", None) or {}
    change_24h = float(raw.get("change_24h", 0.0) or 0.0)
    price = float(raw.get("price", 0.0) or 0.0)
    value = max(0.0, min(1.0, 0.5 + change_24h / 20.0))
    return SubsystemReading(
        name="coingecko_btc",
        value=value,
        confidence=0.8 if price > 0 else 0.0,
        state=f"BTC ${price:,.0f} ({change_24h:+.2f}%)",
    )


# Crude bullish/bearish keyword lists for community sentiment scoring.
# Production-grade NLP belongs elsewhere; this is a directional
# heuristic over headlines only.
_COMM_BULL_KW = ("rally", "surge", "bull", "moon", "pump", "soar",
                 "breakout", "record high", "all-time", "ath", "boom")
_COMM_BEAR_KW = ("crash", "drop", "bear", "dump", "plunge", "tank",
                 "selloff", "collapse", "crater", "wipe out", "rout")


def _map_community(items_hn: list, items_reddit: list) -> SubsystemReading:
    """Reddit + Hacker News headlines → SubsystemReading.

    Crude keyword scoring per item: +1 (bullish kw match), -1 (bearish
    kw match), 0 (neither). Average → mapped from [-1, 1] to [0, 1].
    Confidence scales with the count of items processed and the share
    of items with any keyword hit (heavy-no-keyword pulls drop confidence).
    """
    items = (items_hn or []) + (items_reddit or [])
    if not items:
        return SubsystemReading(
            name="community_sentiment", value=0.5, confidence=0.0,
            state="no_posts",
        )
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


def _map_fred(item) -> SubsystemReading:
    """FRED (UNRATE — US unemployment rate) → SubsystemReading.

    Lower unemployment ⇒ stronger economy ⇒ higher confidence. Linear
    map: 3% → 1.0, 8% → 0.0, clamped. The numeric value lives in
    item.raw["value"] as a string per fetch_fred's CSV parse.
    """
    if item is None:
        return SubsystemReading(
            name="fred_unrate", value=0.5, confidence=0.0, state="unavailable",
        )
    raw = getattr(item, "raw", None) or {}
    try:
        unrate = float(raw.get("value", "nan"))
    except (TypeError, ValueError):
        return SubsystemReading(
            name="fred_unrate", value=0.5, confidence=0.0, state="parse_error",
        )
    if unrate != unrate:  # NaN
        return SubsystemReading(
            name="fred_unrate", value=0.5, confidence=0.0, state="nan",
        )
    # Map 3..8% → 1..0
    value = max(0.0, min(1.0, (8.0 - unrate) / 5.0))
    return SubsystemReading(
        name="fred_unrate",
        value=float(value),
        confidence=0.9,  # FRED is authoritative
        state=f"UNRATE={unrate:.1f}%",
    )


def _map_noaa_climate(item) -> SubsystemReading:
    """NOAA NCEI Climate Data Online record → SubsystemReading.

    The daily climate record is an environmental-context input: a *present,
    authoritative* reading is a stable, high-confidence signal (value 0.75).
    A missing key/record degrades to a neutral, zero-confidence reading so the
    field simply ignores it. State carries the datatype + latest value.
    """
    if item is None:
        return SubsystemReading(
            name="noaa_climate", value=0.5, confidence=0.0, state="unavailable",
        )
    raw = getattr(item, "raw", None) or {}
    count = int(raw.get("count", 0)) if isinstance(raw, dict) else 0
    return SubsystemReading(
        name="noaa_climate",
        value=0.75,
        confidence=0.8,
        state=f"{count}_datasets",
    )


def _map_local_action(stats) -> SubsystemReading:
    """Recent local-machine action verdicts → SubsystemReading.

    This is the organism grounding its OWN moves back into the Master Formula:
    the coherence of what its hands are doing feeds Λ(t) like any external
    source. ``value`` = the recent approve ratio (a body acting within the
    conscience/β-stability island reads as coherent); ``confidence`` scales with
    how many moves we have seen. No activity → neutral, zero-confidence.
    """
    if not stats or not stats.get("count"):
        return SubsystemReading(
            name="local_action", value=0.5, confidence=0.0, state="idle",
        )
    count = int(stats.get("count", 0))
    ratio = stats.get("approve_ratio")
    value = float(ratio) if ratio is not None else 0.5
    import math
    confidence = min(0.9, math.tanh(count / 20.0))
    return SubsystemReading(
        name="local_action",
        value=max(0.0, min(1.0, value)),
        confidence=confidence,
        state=f"{count}_moves_{stats.get('veto_count', 0)}_vetoed",
    )


def _map_usgs_water(item) -> SubsystemReading:
    """USGS Water Data collections snapshot → SubsystemReading.

    Reachable, keyed water-data service = a stable environmental-context input.
    value scales gently with how many collections responded (tanh-saturated),
    so a richer response reads as marginally higher coherence. Absent → neutral.
    """
    if item is None:
        return SubsystemReading(
            name="usgs_water", value=0.5, confidence=0.0, state="unavailable",
        )
    raw = getattr(item, "raw", None) or {}
    count = int(raw.get("count", 0)) if isinstance(raw, dict) else 0
    import math
    value = 0.5 + 0.5 * math.tanh(count / 20.0)
    return SubsystemReading(
        name="usgs_water",
        value=float(value),
        confidence=0.8,
        state=f"{count}_collections",
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
                 observer=None):
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
        self.engine = LambdaEngine()
        self._sources: Dict[str, SourceState] = {}
        self._fetchers: Dict[str, Callable[[], Awaitable[Optional[SubsystemReading]]]] = {}
        self._last_state_dict: Optional[dict] = None
        self._step_lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._trace_path = trace_path or (
            Path(__file__).resolve().parents[2] / "state" / "hnc_live_trace.jsonl"
        )
        self._trace_path.parent.mkdir(parents=True, exist_ok=True)

        # Built-in sources — only wire if their bridges import cleanly.
        self._wire_default_sources()

        # Optional observer attach. Lazy-import + try/except so any
        # observer issue (missing module, missing numpy in sandbox) can
        # NEVER break daemon startup or the compute loop. The observer
        # is purely an output channel from this loop's perspective.
        self._observer = observer
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

    # ─── source registration ────────────────────────────────────

    def register_source(
        self,
        name: str,
        interval_s: float,
        fetcher: Callable[[], Awaitable[Optional[SubsystemReading]]],
    ) -> None:
        """Add a source. ``fetcher`` is an async callable that returns a
        SubsystemReading or None. The daemon handles cadence and retry.
        """
        self._sources[name] = SourceState(name=name, interval_s=interval_s)
        self._fetchers[name] = fetcher
        logger.info("HNC daemon: registered source %s @ %ss", name, interval_s)

    def _wire_default_sources(self) -> None:
        # Schumann
        try:
            from aureon.harmonic.aureon_schumann_resonance_bridge import SchumannResonanceBridge
            bridge = SchumannResonanceBridge()

            async def fetch_schumann():
                # SchumannResonanceBridge.get_live_data() is sync; run in thread.
                reading = await asyncio.to_thread(bridge.get_live_data)
                return _map_schumann(reading) if reading else None

            self.register_source("schumann", SCHUMANN_INTERVAL, fetch_schumann)
        except Exception as exc:
            logger.warning("HNC daemon: schumann not wired (%s)", exc)

        # Space weather
        try:
            from aureon.data_feeds.aureon_space_weather_bridge import SpaceWeatherBridge
            sw = SpaceWeatherBridge()

            async def fetch_space_weather():
                reading = await asyncio.to_thread(sw.get_live_data)
                return _map_space_weather(reading) if reading else None

            self.register_source("space_weather", SPACE_WEATHER_INTERVAL, fetch_space_weather)
        except Exception as exc:
            logger.warning("HNC daemon: space_weather not wired (%s)", exc)

        # GDELT
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            ingester = WorldDataIngester()

            async def fetch_gdelt():
                items = await asyncio.to_thread(ingester.fetch_gdelt, "world", 25)
                return _map_gdelt(items)

            self.register_source("gdelt", GDELT_INTERVAL, fetch_gdelt)
        except Exception as exc:
            logger.warning("HNC daemon: gdelt not wired (%s)", exc)

        # ─── Stage AF: macro context (VIX/DXY/fear-greed/forex) ──
        try:
            from aureon.data_feeds.global_financial_feed import GlobalFinancialFeed
            macro_feed = GlobalFinancialFeed()

            async def fetch_macro():
                snap = await asyncio.to_thread(macro_feed.get_snapshot)
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
                return _map_coingecko(item) if item is not None else None

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
                return _map_community(hn, reddit)

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
                return _map_fred(item) if item is not None else None

            self.register_source("fred_unrate", FRED_INTERVAL, fetch_fred_unrate)
        except Exception as exc:
            logger.warning("HNC daemon: fred_unrate not wired (%s)", exc)

        # ─── Phase 16: NOAA NCEI climate (keyed — NOAA_API_KEY) ───
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            noaa_ingester = WorldDataIngester()

            async def fetch_noaa_climate():
                item = await asyncio.to_thread(noaa_ingester.fetch_noaa_climate)
                return _map_noaa_climate(item)

            self.register_source("noaa_climate", NOAA_CDO_INTERVAL, fetch_noaa_climate)
        except Exception as exc:
            logger.warning("HNC daemon: noaa_climate not wired (%s)", exc)

        # ─── Phase 16: USGS Water Data (keyed — USGS_API_KEY) ─────
        try:
            from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
            usgs_ingester = WorldDataIngester()

            async def fetch_usgs_water():
                item = await asyncio.to_thread(usgs_ingester.fetch_usgs_water)
                return _map_usgs_water(item)

            self.register_source("usgs_water", USGS_WATER_INTERVAL, fetch_usgs_water)
        except Exception as exc:
            logger.warning("HNC daemon: usgs_water not wired (%s)", exc)

        # ─── Phase 18: the organism's own local-machine moves ─────
        # Reads recent grounded-action verdicts off the bus (no operator import
        # cycle) so Λ(t) incorporates what the body is doing to its own machine.
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            _action_bus = get_thought_bus()

            from aureon.core.aureon_thought_bus import payload_of, topic_of

            def _read_action_stats():
                recent = _action_bus.get_recent(200) or []
                verdicts = [
                    payload_of(t)
                    for t in recent
                    if topic_of(t) == "operator.action.verdict"
                ]
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

    # ─── per-source pull loop ──────────────────────────────────

    async def _source_loop(self, name: str) -> None:
        st = self._sources[name]
        fetch = self._fetchers[name]
        while not self._stop.is_set():
            try:
                reading = await fetch()
                if reading is not None:
                    st.last_reading = reading
                    st.last_fetch_ts = time.time()
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
                            mt.ingest(name, float(reading.value), st.last_fetch_ts)
                    except Exception:
                        pass
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

    async def _compute_loop(self) -> None:
        while not self._stop.is_set():
            readings: List[SubsystemReading] = [
                st.last_reading for st in self._sources.values()
                if st.last_reading is not None
            ]
            async with self._step_lock:
                state = self.engine.step(readings)
            self._last_state_dict = state.to_dict()
            self._append_trace(self._last_state_dict, readings)

            # Phase 19 — publish the LIVE field on the thought bus so the whole
            # organism can sense it. The QueenConscience SLS veto, the grounded-
            # action gate, and four other subscribers all read
            # ``symbolic.life.pulse``; without this edge the daemon's real field
            # stayed trapped in the JSONL trace and every consumer degraded to
            # "unknown" in production. Guarded — a bus hiccup never stops the loop.
            try:
                from aureon.core.aureon_thought_bus import Thought, get_thought_bus

                sd = self._last_state_dict
                get_thought_bus().publish(Thought(
                    source="hnc_live_daemon", topic="symbolic.life.pulse",
                    payload={
                        "symbolic_life_score": sd.get("symbolic_life_score"),
                        "coherence_gamma": sd.get("coherence_gamma"),
                        "consciousness_psi": sd.get("consciousness_psi"),
                        "consciousness_level": sd.get("consciousness_level"),
                        "lambda_t": sd.get("lambda_t"),
                        "source": "hnc_live_daemon",
                    },
                ))
            except Exception as exc:
                logger.debug("symbolic.life.pulse publish failed: %s", exc)

            # Feed the engine state into the attached observer. Wrapped
            # so any observer error (numpy missing in sandbox, scipy
            # crash on a degenerate window, etc.) cannot interrupt the
            # compute loop — the daemon's job is to keep ticking.
            if self._observer is not None:
                try:
                    self._observer.ingest_state(state)
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
            row = {
                "ts": state_dict.get("timestamp"),
                "step": state_dict.get("step"),
                "lambda_t": state_dict.get("lambda_t"),
                "consciousness_psi": state_dict.get("consciousness_psi"),
                "consciousness_level": state_dict.get("consciousness_level"),
                "coherence_gamma": state_dict.get("coherence_gamma"),
                "symbolic_life_score": state_dict.get("symbolic_life_score"),
                "sources": {
                    r.name: {"value": r.value, "confidence": r.confidence, "state": r.state}
                    for r in readings
                },
            }
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
        # Final persist so the lighthouse echo survives shutdown.
        try:
            self.engine.save_history()
        except Exception:
            pass
        logger.info("HNC live daemon stopped.")

    async def _stop_after(self, duration_s: float) -> None:
        await asyncio.sleep(duration_s)
        self._stop.set()


# ─── module main — quick smoke test ──────────────────────────────

if __name__ == "__main__":
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
