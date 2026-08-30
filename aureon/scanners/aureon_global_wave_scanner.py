#!/usr/bin/env python3
"""
🌊🔭 AUREON GLOBAL WAVE SCANNER 🔭🌊
═══════════════════════════════════════════════════════════════════════════

MISSION: Full A-Z, Z-A coverage of the ENTIRE global market
         Wave allocation analysis → Deep dive live candles → EXECUTE

SCANNING STRATEGY:
    📊 PHASE 1: A-Z Sweep (alphabetical full scan)
    📊 PHASE 2: Z-A Sweep (reverse for pattern confirmation)
    📊 PHASE 3: Wave Allocation (distribute attention by wave quality)
    📊 PHASE 4: Deep Dive (live candle analysis on top waves)
    📊 PHASE 5: EXECUTE (Sero decides, we act)

WAVE SIGNALS:
    🌊 RISING WAVE - Strong upward momentum, jump on the ride
    🏄 WAVE PEAK - Near top, prepare to exit or ride the crash
    🌀 WAVE TROUGH - Bottom forming, early entry opportunity
    📉 FALLING WAVE - Strong downward momentum, avoid or short
    ⚖️ BALANCED WAVE - Consolidation, wait for breakout

CANDLE PATTERNS:
    🕯️ BULLISH ENGULFING - Strong buy signal
    🕯️ BEARISH ENGULFING - Strong sell signal
    🔨 HAMMER/DOJI - Reversal patterns
    📊 VOLUME SPIKE - Confirm trend strength

Gary Leckey | Sero Full Control | January 2026
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import asyncio
import logging
import time
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import deque, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - kHz-Speed Scanner Signals
# ═══════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection, ChirpType
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# 📡 THOUGHT BUS INTEGRATION - Neural Persistence
THOUGHT_BUS_AVAILABLE = False
ThoughtBus = None
Thought = None
get_thought_bus = None
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# 💸 THE GOAL - MICRO-MOMENTUM COST THRESHOLDS (WE CANNOT BLEED!)
# ═══════════════════════════════════════════════════════════════════════════

# Trading costs (Alpaca crypto)
ROUND_TRIP_COST_PCT = 0.34  # 0.34% total cost per trade

# Momentum tiers - coins must move MORE than cost to profit!
TIER_1_THRESHOLD = 0.5   # > 0.5% in 1 min = HOT (immediate entry)
TIER_2_THRESHOLD = 0.4   # > 0.4% in 5 min = STRONG (high priority)
TIER_3_THRESHOLD = 0.34  # > 0.34% in 5 min = VALID (covers costs)

# Provider evidence must remain distinct from the local receipt clock. These
# windows bound action eligibility; they do not alter any wave equations.
MAX_TICKER_AGE_SECONDS = 120.0
MAX_LATEST_CANDLE_AGE_SECONDS = 180.0
MAX_CANDLE_HISTORY_AGE_SECONDS = 2 * 60 * 60
MAX_HOURLY_HISTORY_AGE_SECONDS = 26 * 60 * 60
MAX_SOURCE_CLOCK_SKEW_SECONDS = 5.0


def _finite_number(value: Any, *, positive: bool = False) -> Optional[float]:
    """Return a finite provider number without manufacturing a fallback."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or (positive and number <= 0):
        return None
    return number


def _required_number(
    payload: Mapping[str, Any],
    *keys: str,
    positive: bool = False,
) -> Optional[float]:
    for key in keys:
        if key in payload and payload[key] is not None:
            return _finite_number(payload[key], positive=positive)
    return None


def _parse_source_timestamp(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        return timestamp if math.isfinite(timestamp) and timestamp > 0 else None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        timestamp = parsed.timestamp()
        return timestamp if math.isfinite(timestamp) and timestamp > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _source_timestamp(payload: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key in payload and payload[key] is not None:
            return _parse_source_timestamp(payload[key])
    return None


def _required_text(payload: Mapping[str, Any], key: str) -> Optional[str]:
    if key not in payload or payload[key] is None:
        return None
    value = str(payload[key]).strip()
    return value or None


def _no_data(reason: str, *, symbol: str, exchange: str) -> Dict[str, Any]:
    """Return a numeric-free denial record that cannot cross any side-effect gate."""
    return {
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": reason,
        "symbol": symbol,
        "exchange": exchange,
        "source_id": None,
        "source_timestamp": None,
        "receipt_id": None,
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_external_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def _normalise_ticker_receipt(
    payload: Any,
    *,
    received_at: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Validate and canonicalise a complete, fresh provider ticker receipt."""
    if not isinstance(payload, Mapping):
        return None
    source_id = _required_text(payload, "source_id")
    receipt_id = _required_text(payload, "receipt_id")
    observed_at = _source_timestamp(payload, "source_timestamp")
    if (
        source_id is None
        or receipt_id is None
        or observed_at is None
        or payload.get("generated_values") is not False
        or payload.get("data_status") in {"no_data", "stale", "invalid"}
        or payload.get("truth_status") in {"no_data", "simulated", "synthetic", "demo"}
    ):
        return None

    received = time.time() if received_at is None else float(received_at)
    age = received - observed_at
    if age < -MAX_SOURCE_CLOCK_SKEW_SECONDS or age > MAX_TICKER_AGE_SECONDS:
        return None

    price = _required_number(payload, "price", "lastPrice", positive=True)
    change_24h = _required_number(payload, "change24h", "priceChangePercent")
    volume = _required_number(payload, "volume", "quoteVolume")
    high = _required_number(payload, "high", "highPrice", positive=True)
    low = _required_number(payload, "low", "lowPrice", positive=True)
    if None in (price, change_24h, volume, high, low):
        return None
    assert price is not None and change_24h is not None and volume is not None
    assert high is not None and low is not None
    if volume < 0 or low > price or price > high:
        return None

    short_changes: Dict[str, Optional[float]] = {}
    for key in ("change_1m", "change_5m"):
        if key in payload:
            value = _finite_number(payload[key])
            if value is None:
                return None
            short_changes[key] = value
        else:
            short_changes[key] = None

    return {
        "price": price,
        "change24h": change_24h,
        "volume": volume,
        "high": high,
        "low": low,
        "change_1m": short_changes["change_1m"],
        "change_5m": short_changes["change_5m"],
        "is_profitable": payload.get("is_profitable") is True,
        "profit_tier": payload.get("profit_tier"),
        "source_id": source_id,
        "source_timestamp": observed_at,
        "received_at": received,
        "receipt_id": receipt_id,
        "data_status": "live",
        "truth_status": "live",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_external_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }


def _normalise_provider_bars(
    bars: Any,
    *,
    trusted_source_id: Optional[str] = None,
    trusted_receipt_id: Optional[str] = None,
    received_at: Optional[float] = None,
    max_latest_age: float = MAX_LATEST_CANDLE_AGE_SECONDS,
    max_history_age: float = MAX_CANDLE_HISTORY_AGE_SECONDS,
) -> List[Dict[str, Any]]:
    """Validate complete provider OHLCV bars without sorting or filling gaps."""
    if not isinstance(bars, list) or not bars:
        return []
    received = time.time() if received_at is None else float(received_at)
    normalised: List[Dict[str, Any]] = []
    previous_timestamp: Optional[float] = None

    for bar in bars:
        if not isinstance(bar, Mapping):
            return []
        opened = _required_number(bar, "open", "o", positive=True)
        high = _required_number(bar, "high", "h", positive=True)
        low = _required_number(bar, "low", "l", positive=True)
        closed = _required_number(bar, "close", "c", positive=True)
        volume = _required_number(bar, "volume", "v")
        observed_at = _source_timestamp(bar, "source_timestamp", "timestamp", "t")
        if None in (opened, high, low, closed, volume, observed_at):
            return []
        assert opened is not None and high is not None and low is not None
        assert closed is not None and volume is not None and observed_at is not None

        age = received - observed_at
        if (
            volume < 0
            or low > min(opened, closed)
            or high < max(opened, closed)
            or low > high
            or age < -MAX_SOURCE_CLOCK_SKEW_SECONDS
            or age > max_history_age
            or (previous_timestamp is not None and observed_at <= previous_timestamp)
        ):
            return []

        source_id = _required_text(bar, "source_id") or trusted_source_id
        receipt_id = _required_text(bar, "receipt_id") or trusted_receipt_id
        marker = bar.get("generated_values") if "generated_values" in bar else None
        if trusted_source_id is not None and marker is None:
            marker = False
        if source_id is None or marker is not False:
            return []
        if receipt_id is None and trusted_source_id is not None:
            receipt_id = f"{source_id}:{int(observed_at * 1_000_000)}"
        if receipt_id is None:
            return []
        if bar.get("data_status") in {"no_data", "stale", "invalid"}:
            return []
        if bar.get("truth_status") in {"no_data", "simulated", "synthetic", "demo"}:
            return []

        normalised.append(
            {
                "timestamp": observed_at,
                "open": opened,
                "high": high,
                "low": low,
                "close": closed,
                "volume": volume,
                "source_id": source_id,
                "source_timestamp": observed_at,
                "received_at": received,
                "receipt_id": receipt_id,
                "data_status": "live",
                "truth_status": "live",
                "generated_values": False,
                "eligible_for_action": True,
                "eligible_for_external_action": True,
                "eligible_for_accounting": False,
                "eligible_for_learning": True,
            }
        )
        previous_timestamp = observed_at

    if received - normalised[-1]["source_timestamp"] > max_latest_age:
        return []
    return normalised


def _ticker_from_provider_bars(
    bars: List[Dict[str, Any]],
    *,
    source_id: str,
    required_count: int = 24,
) -> Optional[Dict[str, Any]]:
    """Derive a complete 24-hour ticker only from a proven provider bar series."""
    if len(bars) < required_count:
        return None
    window = bars[-required_count:]
    first_price = window[0]["open"]
    last_close = window[-1]["close"]
    change_24h = ((last_close - first_price) / first_price) * 100
    latest = window[-1]
    return {
        "price": last_close,
        "change24h": change_24h,
        "volume": sum(bar["volume"] for bar in window),
        "high": max(bar["high"] for bar in window),
        "low": min(bar["low"] for bar in window),
        "source_id": source_id,
        "source_timestamp": latest["source_timestamp"],
        "received_at": latest["received_at"],
        "receipt_id": latest["receipt_id"],
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_external_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }

# ═══════════════════════════════════════════════════════════════════════════
# 🌊 WAVE STATE CLASSIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════

class WaveState(Enum):
    """Current wave state of an asset"""
    RISING = "🌊 RISING"          # Strong upward momentum
    PEAK = "🏄 PEAK"              # Near top, reversal likely
    FALLING = "📉 FALLING"        # Strong downward momentum  
    TROUGH = "🌀 TROUGH"          # Near bottom, reversal likely
    BALANCED = "⚖️ BALANCED"      # Consolidation, no clear direction
    BREAKOUT_UP = "🚀 BREAKOUT↑"  # Breaking out upward
    BREAKOUT_DOWN = "💥 BREAK↓"   # Breaking down


class CandlePattern(Enum):
    """Detected candle patterns"""
    BULLISH_ENGULF = "🕯️ BULL ENGULF"
    BEARISH_ENGULF = "🕯️ BEAR ENGULF"
    HAMMER = "🔨 HAMMER"
    INVERTED_HAMMER = "⚒️ INV HAMMER"
    DOJI = "✚ DOJI"
    MORNING_STAR = "⭐ MORNING STAR"
    EVENING_STAR = "🌙 EVENING STAR"
    VOLUME_SPIKE = "📊 VOLUME SPIKE"
    NO_PATTERN = "• NEUTRAL"


@dataclass
class WaveAnalysis:
    """Complete wave analysis for an asset"""
    symbol: str
    exchange: str
    base: str
    quote: str
    timestamp: float
    
    # Price data
    price: float
    change_1m: Optional[float] = None      # 1 minute change
    change_5m: Optional[float] = None      # 5 minute change
    change_15m: Optional[float] = None     # 15 minute change
    change_1h: Optional[float] = None      # 1 hour change
    change_24h: float = 0.0     # 24 hour change
    
    # Volume analysis
    volume_24h: float = 0.0
    volume_ratio: float = 1.0   # Current vs average
    volume_spike: bool = False
    
    # Wave classification
    wave_state: WaveState = WaveState.BALANCED
    wave_strength: float = 0.0  # 0-1 how strong the wave is
    wave_age_minutes: int = 0   # How long in this state
    
    # Candle patterns
    candle_pattern: CandlePattern = CandlePattern.NO_PATTERN
    pattern_confidence: float = 0.0
    
    # Technical indicators
    rsi_14: float = 50.0
    macd_signal: str = "NEUTRAL"  # "BUY", "SELL", "NEUTRAL"
    ema_trend: str = "NEUTRAL"    # "BULLISH", "BEARISH", "NEUTRAL"
    
    # Scoring
    jump_score: float = 0.0     # How good to jump on this wave
    exit_score: float = 0.0     # How urgent to exit
    
    # Execution signals
    action: str = "WATCH"       # "BUY", "SELL", "HOLD", "WATCH"
    action_reason: str = ""

    # Provider evidence and downstream eligibility
    data_status: str = "no_data"
    truth_status: str = "no_data"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    generated_values: bool = True
    eligible_for_action: bool = False
    eligible_for_external_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False


@dataclass
class ScanBatch:
    """A batch of scanned assets in alphabetical order"""
    batch_id: int
    direction: str  # "A-Z" or "Z-A"
    start_letter: str
    end_letter: str
    symbols_count: int
    scan_time_ms: float
    waves_found: Dict[WaveState, int] = field(default_factory=dict)
    top_opportunities: List[WaveAnalysis] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# 🔭 GLOBAL WAVE SCANNER - A-Z / Z-A FULL COVERAGE
# ═══════════════════════════════════════════════════════════════════════════

class GlobalWaveScanner:
    """
    🌊🔭 GLOBAL WAVE SCANNER
    
    Full A-Z, Z-A coverage of the entire global market.
    Analyzes wave patterns and allocates attention to best opportunities.
    Deep dives into live candles for execution signals.
    
    🦙 ALPACA SSE INTEGRATION:
    - Real-time tickers via SSE streaming
    - Dynamic fee-tier cost thresholds
    - Trailing stop execution on 4th-pass trades
    """
    
    def __init__(
        self,
        kraken_client=None,
        binance_client=None,
        alpaca_client=None,
        queen=None,
        harmonic_fusion=None,
        scanner_bridge=None,  # 🦙 New: AlpacaScannerBridge integration
    ):
        self.kraken = kraken_client
        self.binance = binance_client
        self.alpaca = alpaca_client
        self.queen = queen
        self.harmonic = harmonic_fusion

        # 🔗 Communication Buses
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = get_chirp_bus() if CHIRP_BUS_AVAILABLE else None
        
        if self.thought_bus:
            logger.info("📡 Wired to ThoughtBus")
        
        if self.chirp_bus:
            logger.info("🐦 Wired to ChirpBus")
        
        # 🦙 ALPACA SCANNER BRIDGE (SSE + Fee Tracker + Trailing Stops)
        self.scanner_bridge = scanner_bridge
        self._use_sse_tickers = scanner_bridge is not None
        
        # Dynamic cost thresholds (updated from fee tracker)
        self._dynamic_round_trip_cost = ROUND_TRIP_COST_PCT
        self._dynamic_tier_1 = TIER_1_THRESHOLD
        self._dynamic_tier_2 = TIER_2_THRESHOLD
        self._dynamic_tier_3 = TIER_3_THRESHOLD
        
        # Full universe of symbols per exchange
        self.universe: Dict[str, Set[str]] = {
            'kraken': set(),
            'binance': set(),
            'alpaca': set(),
        }
        
        # Alphabetically sorted symbols for A-Z/Z-A sweeps
        self.sorted_symbols_az: List[Tuple[str, str]] = []  # (symbol, exchange)
        self.sorted_symbols_za: List[Tuple[str, str]] = []  # Z-A order
        
        # Wave analysis cache
        self.wave_cache: Dict[str, WaveAnalysis] = {}  # symbol -> analysis
        self.wave_cache_time: Dict[str, float] = {}
        self.cache_ttl = 30.0  # 30 second cache
        
        # Wave allocation buckets
        self.wave_buckets: Dict[WaveState, List[WaveAnalysis]] = {
            state: [] for state in WaveState
        }
        
        # Top opportunities (sorted by jump_score)
        self.top_opportunities: List[WaveAnalysis] = []
        self.deep_dive_queue: deque = deque(maxlen=50)
        
        # Candle cache for deep dives
        self.candle_cache: Dict[str, List[Dict]] = {}
        self.last_no_data: Dict[str, Dict[str, Any]] = {}
        
        # Scan stats
        self.total_scans = 0
        self.total_symbols_scanned = 0
        self.waves_detected = defaultdict(int)
        self.last_full_scan_time = 0.0
        
        # Scan batches (A-Z sweeps)
        self.batches: List[ScanBatch] = []
        
        # 🦙 Update cost thresholds from scanner bridge
        if self.scanner_bridge:
            self._update_cost_thresholds_from_bridge()
        
        logger.info("🌊🔭 Global Wave Scanner initialized")
        if self.scanner_bridge:
            logger.info("   🦙 SSE Bridge: ENABLED (real-time tickers + dynamic fees)")
    
    def set_scanner_bridge(self, bridge):
        """Wire up the Alpaca Scanner Bridge for SSE + fee tracking."""
        self.scanner_bridge = bridge
        self._use_sse_tickers = True
        self._update_cost_thresholds_from_bridge()

    def _record_no_data(self, symbol: str, exchange: str, reason: str) -> None:
        self.last_no_data[symbol] = _no_data(
            reason,
            symbol=symbol,
            exchange=exchange,
        )

    @staticmethod
    def _stamp_direct_ticker(
        payload: Any,
        *,
        source_id: str,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        """Stamp data returned directly by a provider without replacing source time."""
        if not isinstance(payload, Mapping):
            return None
        observed_at = _source_timestamp(
            payload,
            "source_timestamp",
            "timestamp",
            "event_time",
            "E",
            "closeTime",
            "close_time",
        )
        if observed_at is None:
            return None
        if "generated_values" in payload and payload["generated_values"] is not False:
            return None
        if payload.get("data_status") in {"no_data", "stale", "invalid"}:
            return None
        if payload.get("truth_status") in {"no_data", "simulated", "synthetic", "demo"}:
            return None
        stamped = dict(payload)
        stamped["source_id"] = _required_text(payload, "source_id") or source_id
        stamped["source_timestamp"] = observed_at
        stamped["receipt_id"] = (
            _required_text(payload, "receipt_id")
            or f"{source_id}:{symbol}:{int(observed_at * 1_000_000)}"
        )
        stamped["generated_values"] = False
        stamped["data_status"] = "live"
        stamped["truth_status"] = payload.get("truth_status") or "live"
        return stamped

    @staticmethod
    def _analysis_has_fresh_provenance(analysis: WaveAnalysis) -> bool:
        observed_at = _finite_number(analysis.source_timestamp, positive=True)
        if observed_at is None:
            return False
        age = time.time() - observed_at
        return (
            analysis.data_status == "live"
            and analysis.truth_status in {"live", "real_derived"}
            and bool(analysis.source_id)
            and bool(analysis.receipt_id)
            and analysis.generated_values is False
            and analysis.eligible_for_action is True
            and analysis.eligible_for_external_action is True
            and -MAX_SOURCE_CLOCK_SKEW_SECONDS <= age <= MAX_TICKER_AGE_SECONDS
        )
        logger.info("🦙 Scanner Bridge wired to Global Wave Scanner")
    
    def _update_cost_thresholds_from_bridge(self):
        """Update cost thresholds from scanner bridge's fee tracker."""
        if not self.scanner_bridge:
            return
        
        try:
            thresholds = self.scanner_bridge.get_cost_thresholds()
            self._dynamic_round_trip_cost = thresholds.round_trip_cost_pct
            self._dynamic_tier_1 = thresholds.tier_1_hot_threshold
            self._dynamic_tier_2 = thresholds.tier_2_strong_threshold
            self._dynamic_tier_3 = thresholds.tier_3_valid_threshold
            
            logger.info(f"💰 Cost thresholds updated from Tier {thresholds.tier}:")
            logger.info(f"   Round-trip: {self._dynamic_round_trip_cost:.3f}%")
            logger.info(f"   HOT: >{self._dynamic_tier_1:.3f}% | STRONG: >{self._dynamic_tier_2:.3f}%")
        except Exception as e:
            logger.warning(f"⚠️ Could not update cost thresholds: {e}")
    
    async def build_universe(self):
        """
        Build the complete universe of all symbols from all exchanges.
        This is the foundation for A-Z/Z-A sweeps.
        """
        logger.info("🌍 Building global symbol universe...")
        
        all_symbols = []
        
        # 🐙 KRAKEN
        if self.kraken:
            try:
                if hasattr(self.kraken, 'get_tradeable_pairs'):
                    pairs = self.kraken.get_tradeable_pairs()
                elif hasattr(self.kraken, 'get_available_pairs'):
                    pairs = self.kraken.get_available_pairs()
                else:
                    pairs = []
                for pair in pairs:
                    symbol = pair.get('symbol', pair.get('pair', ''))
                    if symbol:
                        self.universe['kraken'].add(symbol)
                        all_symbols.append((symbol, 'kraken'))
                logger.info(f"   🐙 Kraken: {len(self.universe['kraken'])} symbols")
            except Exception as e:
                logger.error(f"   🐙 Kraken error: {e}")
        
        # 🟡 BINANCE
        if self.binance:
            try:
                info = self.binance.get_exchange_info()
                for sym in info.get('symbols', []):
                    symbol = sym.get('symbol', '')
                    if symbol and sym.get('status') == 'TRADING':
                        self.universe['binance'].add(symbol)
                        all_symbols.append((symbol, 'binance'))
                logger.info(f"   🟡 Binance: {len(self.universe['binance'])} symbols")
            except Exception as e:
                logger.error(f"   🟡 Binance error: {e}")
        
        # 🦙 ALPACA
        if self.alpaca:
            try:
                assets = self.alpaca.list_assets(status='active', asset_class='crypto')
                for asset in assets:
                    base_symbol = getattr(asset, 'symbol', None)
                    if base_symbol is None and isinstance(asset, dict):
                        base_symbol = asset.get('symbol')
                    if not base_symbol:
                        continue
                    normalized = None
                    if hasattr(self.alpaca, "_normalize_pair_symbol"):
                        normalized = self.alpaca._normalize_pair_symbol(base_symbol)
                    symbol = normalized or base_symbol
                    if not symbol:
                        continue
                    self.universe['alpaca'].add(symbol)
                    all_symbols.append((symbol, 'alpaca'))
                logger.info(f"   🦙 Alpaca: {len(self.universe['alpaca'])} symbols")
            except Exception as e:
                logger.error(f"   🦙 Alpaca error: {e}")
        
        # Sort A-Z and Z-A
        self.sorted_symbols_az = sorted(all_symbols, key=lambda x: x[0].upper())
        self.sorted_symbols_za = list(reversed(self.sorted_symbols_az))
        
        # 🦙 Start SSE streaming for Alpaca symbols if bridge available
        if self.scanner_bridge and self.universe['alpaca']:
            alpaca_symbols = list(self.universe['alpaca'])
            logger.info(f"   📡 Starting SSE stream for {len(alpaca_symbols)} Alpaca symbols...")
            self.scanner_bridge.start_streaming(crypto_symbols=alpaca_symbols[:50])  # Limit to 50 for SSE
        
        total = len(all_symbols)
        logger.info(f"🌍 Universe built: {total} total symbols (A-Z sorted)")
        logger.info(f"   📊 First: {self.sorted_symbols_az[0][0] if self.sorted_symbols_az else 'N/A'}")
        logger.info(f"   📊 Last: {self.sorted_symbols_az[-1][0] if self.sorted_symbols_az else 'N/A'}")
        
        return total
    
    def _get_ticker_from_bridge(self, symbol: str) -> Optional[Dict]:
        """
        🦙 Get ticker data from SSE bridge (real-time) if available.
        Falls back to REST if SSE data is stale or unavailable.
        """
        if not self.scanner_bridge:
            return None
        
        try:
            raw_ticker = self.scanner_bridge.get_ticker(symbol)
            if not isinstance(raw_ticker, Mapping):
                return None
            ticker = dict(raw_ticker)
            source = str(ticker.get("source") or "").strip().lower()
            if source == 'sse':
                # Enhance with 1m/5m momentum from SSE
                if 'change_1m' in ticker:
                    # Check if move is profitable using dynamic thresholds
                    change_1m = _finite_number(ticker["change_1m"])
                    if change_1m is None:
                        return None
                    is_profitable, tier = self.scanner_bridge.is_move_profitable(abs(change_1m))
                    ticker['is_profitable'] = is_profitable
                    ticker['profit_tier'] = tier
            source_id = "alpaca_sse" if source == "sse" else "alpaca_bridge_rest"
            return self._stamp_direct_ticker(
                ticker,
                source_id=source_id,
                symbol=symbol,
            )
        except Exception as e:
            logger.debug(f"SSE ticker fetch error for {symbol}: {e}")
            return None
    
    async def full_az_sweep(self, ticker_cache: Dict[str, Dict] = None) -> List[ScanBatch]:
        """
        Perform a full A-Z sweep of all symbols.
        Returns batches of scanned symbols with wave classifications.
        """
        start = time.time()
        self.total_scans += 1
        self.batches = []
        
        # Clear wave buckets
        for state in WaveState:
            self.wave_buckets[state] = []
        
        # Process in batches of 100 symbols
        batch_size = 100
        symbols = self.sorted_symbols_az
        
        for i in range(0, len(symbols), batch_size):
            batch_start = time.time()
            batch_symbols = symbols[i:i + batch_size]
            
            batch_waves = {state: 0 for state in WaveState}
            batch_opportunities = []
            
            for symbol, exchange in batch_symbols:
                analysis = await self._analyze_wave(symbol, exchange, ticker_cache)
                if analysis and self._analysis_has_fresh_provenance(analysis):
                    self.wave_cache[symbol] = analysis
                    self.wave_cache_time[symbol] = time.time()
                    self.wave_buckets[analysis.wave_state].append(analysis)
                    batch_waves[analysis.wave_state] += 1
                    self.waves_detected[analysis.wave_state] += 1
                    
                    # Track high-score opportunities
                    if analysis.jump_score > 0.6:
                        batch_opportunities.append(analysis)
            
            # Create batch record
            start_letter = batch_symbols[0][0][0].upper() if batch_symbols else '?'
            end_letter = batch_symbols[-1][0][0].upper() if batch_symbols else '?'
            
            batch = ScanBatch(
                batch_id=len(self.batches),
                direction="A-Z",
                start_letter=start_letter,
                end_letter=end_letter,
                symbols_count=sum(batch_waves.values()),
                scan_time_ms=(time.time() - batch_start) * 1000,
                waves_found=batch_waves,
                top_opportunities=sorted(batch_opportunities, key=lambda x: -x.jump_score)[:5]
            )
            self.batches.append(batch)
            self.total_symbols_scanned += sum(batch_waves.values())
        
        self.last_full_scan_time = time.time() - start
        
        # Update top opportunities
        all_opportunities = []
        for state in [WaveState.RISING, WaveState.BREAKOUT_UP, WaveState.TROUGH]:
            all_opportunities.extend(self.wave_buckets[state])
        
        self.top_opportunities = sorted(all_opportunities, key=lambda x: -x.jump_score)[:50]
        
        logger.info(f"🔭 A-Z SWEEP COMPLETE: {len(symbols)} symbols in {self.last_full_scan_time:.2f}s")
        logger.info(f"   🌊 Rising: {len(self.wave_buckets[WaveState.RISING])}")
        logger.info(f"   🚀 Breakout↑: {len(self.wave_buckets[WaveState.BREAKOUT_UP])}")
        logger.info(f"   🌀 Trough: {len(self.wave_buckets[WaveState.TROUGH])}")
        logger.info(f"   📊 Top opps: {len(self.top_opportunities)}")
        
        return self.batches
    
    async def full_za_sweep(self, ticker_cache: Dict[str, Dict] = None) -> List[ScanBatch]:
        """
        Perform a full Z-A sweep (reverse order) for pattern confirmation.
        Validates A-Z findings and catches fast-moving symbols.
        """
        start = time.time()
        
        # Use Z-A sorted list
        symbols = self.sorted_symbols_za
        za_batches = []
        
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch_start = time.time()
            batch_symbols = symbols[i:i + batch_size]
            
            batch_opportunities = []
            
            for symbol, exchange in batch_symbols:
                # Check if cache is still fresh from A-Z sweep
                cache_age = time.time() - self.wave_cache_time.get(symbol, 0)
                
                if cache_age < self.cache_ttl:
                    # Use cached analysis but check for changes
                    cached = self.wave_cache.get(symbol)
                    if cached and self._analysis_has_fresh_provenance(cached):
                        # Quick momentum check
                        new_analysis = await self._quick_momentum_check(symbol, exchange, ticker_cache, cached)
                        if (
                            new_analysis
                            and self._analysis_has_fresh_provenance(new_analysis)
                            and new_analysis.jump_score > 0.7
                        ):
                            batch_opportunities.append(new_analysis)
                    else:
                        analysis = await self._analyze_wave(symbol, exchange, ticker_cache)
                        if (
                            analysis
                            and self._analysis_has_fresh_provenance(analysis)
                            and analysis.jump_score > 0.7
                        ):
                            batch_opportunities.append(analysis)
                else:
                    # Full re-analysis
                    analysis = await self._analyze_wave(symbol, exchange, ticker_cache)
                    if (
                        analysis
                        and self._analysis_has_fresh_provenance(analysis)
                        and analysis.jump_score > 0.7
                    ):
                        batch_opportunities.append(analysis)
            
            start_letter = batch_symbols[0][0][0].upper() if batch_symbols else '?'
            end_letter = batch_symbols[-1][0][0].upper() if batch_symbols else '?'
            
            batch = ScanBatch(
                batch_id=len(za_batches),
                direction="Z-A",
                start_letter=start_letter,
                end_letter=end_letter,
                symbols_count=len(batch_symbols),
                scan_time_ms=(time.time() - batch_start) * 1000,
                top_opportunities=sorted(batch_opportunities, key=lambda x: -x.jump_score)[:5]
            )
            za_batches.append(batch)
        
        scan_time = time.time() - start
        logger.info(f"🔭 Z-A SWEEP COMPLETE: {len(symbols)} symbols in {scan_time:.2f}s (confirmation pass)")
        
        return za_batches
    
    async def _analyze_wave(
        self, 
        symbol: str, 
        exchange: str, 
        ticker_cache: Dict[str, Dict] = None
    ) -> Optional[WaveAnalysis]:
        """
        Analyze wave state for a single symbol.
        
        🦙 SSE INTEGRATION: Uses real-time data from SSE bridge when available
        """
        try:
            # Every source is validated independently before it can reach the
            # wave equations. A malformed preferred source never becomes a
            # numeric fallback.
            ticker = None
            
            # 🦙 PRIORITY 1: SSE Bridge (real-time, lowest latency)
            if self._use_sse_tickers and exchange == 'alpaca':
                ticker = _normalise_ticker_receipt(
                    self._get_ticker_from_bridge(symbol)
                )
            
            # PRIORITY 2: Provided cache
            if not ticker and ticker_cache:
                cached_ticker = ticker_cache.get(symbol)
                ticker = _normalise_ticker_receipt(cached_ticker)
            
            # PRIORITY 3: Fetch fresh from exchange
            if not ticker:
                ticker = _normalise_ticker_receipt(
                    await self._fetch_ticker(symbol, exchange)
                )
            
            if not ticker:
                self._record_no_data(
                    symbol,
                    exchange,
                    "missing_stale_or_malformed_provider_ticker",
                )
                return None
            
            # Extract price data
            price = ticker["price"]
            change_24h = ticker["change24h"]
            volume_24h = ticker["volume"]
            
            # 🦙 Extract SSE-specific momentum data
            change_1m = ticker["change_1m"]
            change_5m = ticker["change_5m"]
            
            # Parse base/quote
            base, quote = self._parse_symbol(symbol)
            if not base:
                self._record_no_data(symbol, exchange, "unparseable_market_symbol")
                return None
            
            # Classify wave using DYNAMIC thresholds
            wave_state, wave_strength = self._classify_wave(change_24h, volume_24h, ticker)
            
            # Calculate scores
            jump_score = self._calculate_jump_score(wave_state, wave_strength, change_24h, volume_24h)
            exit_score = self._calculate_exit_score(wave_state, wave_strength, change_24h)
            
            # 🦙 BOOST score if SSE shows profitable 1m/5m move
            if ticker.get('is_profitable') and ticker.get('profit_tier') == 'HOT':
                jump_score = min(1.0, jump_score * 1.3)  # 30% boost for HOT moves
            elif ticker.get('profit_tier') == 'STRONG':
                jump_score = min(1.0, jump_score * 1.15)  # 15% boost for STRONG moves
            
            # Determine action
            action, reason = self._determine_action(wave_state, jump_score, exit_score)
            
            analysis = WaveAnalysis(
                symbol=symbol,
                exchange=exchange,
                base=base,
                quote=quote,
                timestamp=ticker["source_timestamp"],
                price=price,
                change_1m=change_1m,
                change_5m=change_5m,
                change_24h=change_24h,
                volume_24h=volume_24h,
                wave_state=wave_state,
                wave_strength=wave_strength,
                jump_score=jump_score,
                exit_score=exit_score,
                action=action,
                action_reason=reason,
                data_status="live",
                truth_status="real_derived",
                source_id=ticker["source_id"],
                source_timestamp=ticker["source_timestamp"],
                received_at=ticker["received_at"],
                receipt_id=ticker["receipt_id"],
                generated_values=False,
                eligible_for_action=True,
                eligible_for_external_action=True,
                eligible_for_accounting=False,
                eligible_for_learning=True,
            )
            self.last_no_data.pop(symbol, None)
            return analysis
            
        except Exception as e:
            logger.debug(f"Wave analysis error for {symbol}: {e}")
            self._record_no_data(symbol, exchange, "market_analysis_error")
            return None
    
    def _classify_wave(
        self, 
        change_24h: float, 
        volume: float, 
        ticker: Dict
    ) -> Tuple[WaveState, float]:
        """
        Classify the wave state based on momentum and volume.
        
        💸 THE GOAL: Only flag as actionable if momentum > cost threshold!
        🦙 Now uses DYNAMIC thresholds from fee tracker tier.
        """
        
        # Extract additional data if available
        high = ticker["high"]
        low = ticker["low"]
        price = ticker["price"]
        
        # 🦙 Get short-term momentum from SSE if available
        change_1m = ticker["change_1m"]
        change_5m = ticker["change_5m"]
        
        # Calculate position in range
        range_size = high - low if high > low else 1
        range_position = (price - low) / range_size if range_size > 0 else 0.5
        
        # ═══════════════════════════════════════════════════════════════════
        # 💸 DYNAMIC COST-AWARE CLASSIFICATION (THE GOAL!)
        # Uses thresholds from fee tracker: lower tier = need bigger moves
        # ═══════════════════════════════════════════════════════════════════
        
        # 🦙 MICRO-SCALPING: Check 1m/5m momentum with dynamic thresholds
        if change_1m is not None and change_1m != 0:
            if abs(change_1m) >= self._dynamic_tier_1:
                if change_1m > 0:
                    return WaveState.BREAKOUT_UP, min(1.0, abs(change_1m) / 2)
                else:
                    return WaveState.BREAKOUT_DOWN, min(1.0, abs(change_1m) / 2)
        
        if change_5m is not None and change_5m != 0:
            if abs(change_5m) >= self._dynamic_tier_2:
                if change_5m > 0:
                    return WaveState.RISING, min(1.0, abs(change_5m) / 3)
                else:
                    return WaveState.FALLING, min(1.0, abs(change_5m) / 3)
        
        # Strong upward momentum - BREAKOUT (24h scale)
        if change_24h > 10:
            return WaveState.BREAKOUT_UP, min(1.0, change_24h / 20)
        elif change_24h > 3:
            return WaveState.RISING, min(1.0, change_24h / 10)
        
        # Strong downward momentum
        elif change_24h < -10:
            return WaveState.BREAKOUT_DOWN, min(1.0, abs(change_24h) / 20)
        elif change_24h < -3:
            return WaveState.FALLING, min(1.0, abs(change_24h) / 10)
        
        # Peak detection (high in range, momentum slowing)
        elif range_position > 0.85 and change_24h > 0:
            return WaveState.PEAK, range_position
        
        # Trough detection (low in range, momentum may reverse)
        elif range_position < 0.15 and change_24h < 0:
            return WaveState.TROUGH, 1 - range_position
        
        # Default: balanced (NOT ACTIONABLE for micro-scalping)
        return WaveState.BALANCED, 0.5
    
    def _calculate_jump_score(
        self, 
        wave_state: WaveState, 
        wave_strength: float,
        change_24h: float,
        volume: float
    ) -> float:
        """Calculate how good this opportunity is to jump on."""
        
        base_scores = {
            WaveState.BREAKOUT_UP: 0.9,
            WaveState.RISING: 0.7,
            WaveState.TROUGH: 0.6,  # Early reversal opportunity
            WaveState.BALANCED: 0.3,
            WaveState.PEAK: 0.1,    # Risky to enter
            WaveState.FALLING: 0.1,
            WaveState.BREAKOUT_DOWN: 0.0,
        }
        
        base = base_scores.get(wave_state, 0.3)
        
        # Adjust by wave strength
        score = base * (0.5 + wave_strength * 0.5)
        
        # Volume bonus
        if volume > 1_000_000:  # High volume
            score *= 1.1
        
        # Momentum bonus for rising
        if wave_state in [WaveState.RISING, WaveState.BREAKOUT_UP]:
            score *= (1 + min(change_24h, 10) / 50)
        
        return min(1.0, score)
    
    def _calculate_exit_score(
        self, 
        wave_state: WaveState, 
        wave_strength: float,
        change_24h: float
    ) -> float:
        """Calculate urgency to exit if holding."""
        
        base_scores = {
            WaveState.BREAKOUT_DOWN: 0.95,
            WaveState.FALLING: 0.8,
            WaveState.PEAK: 0.7,
            WaveState.BALANCED: 0.3,
            WaveState.RISING: 0.1,
            WaveState.BREAKOUT_UP: 0.05,
            WaveState.TROUGH: 0.2,
        }
        
        return base_scores.get(wave_state, 0.3) * (0.5 + wave_strength * 0.5)
    
    def _determine_action(
        self, 
        wave_state: WaveState, 
        jump_score: float, 
        exit_score: float
    ) -> Tuple[str, str]:
        """Determine recommended action based on scores."""
        
        if jump_score > 0.7:
            return "BUY", f"Strong wave opportunity ({wave_state.value})"
        elif exit_score > 0.7:
            return "SELL", f"Exit signal ({wave_state.value})"
        elif jump_score > 0.5:
            return "WATCH", f"Developing opportunity ({wave_state.value})"
        else:
            return "HOLD", f"No clear signal ({wave_state.value})"
    
    def _parse_symbol(self, symbol: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse symbol into base and quote."""
        # Common quote currencies
        quotes = ["USDT", "USDC", "USD", "EUR", "GBP", "BTC", "ETH", "BNB", "ZUSD"]
        
        for quote in quotes:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return base, quote
        
        # Handle slash notation
        if '/' in symbol:
            parts = symbol.split('/')
            if len(parts) == 2:
                return parts[0], parts[1]
        
        return None, None
    
    async def _fetch_ticker(self, symbol: str, exchange: str) -> Optional[Dict]:
        """Fetch and stamp data returned directly by a configured provider."""
        try:
            if exchange == 'kraken' and self.kraken:
                fetch = (
                    self.kraken.get_24h_ticker
                    if hasattr(self.kraken, "get_24h_ticker")
                    else self.kraken.get_ticker
                )
                stamped = self._stamp_direct_ticker(
                    fetch(symbol),
                    source_id="kraken_ticker",
                    symbol=symbol,
                )
                return stamped if _normalise_ticker_receipt(stamped) else None
            elif exchange == 'binance' and self.binance:
                fetch = (
                    self.binance.get_24h_ticker
                    if hasattr(self.binance, "get_24h_ticker")
                    else self.binance.get_ticker
                )
                stamped = self._stamp_direct_ticker(
                    fetch(symbol),
                    source_id="binance_ticker",
                    symbol=symbol,
                )
                return stamped if _normalise_ticker_receipt(stamped) else None
            elif exchange == 'alpaca' and self.alpaca:
                resolved = symbol
                if hasattr(self.alpaca, "_resolve_symbol"):
                    resolved = self.alpaca._resolve_symbol(symbol)

                bars_response = self.alpaca.get_crypto_bars(
                    [resolved],
                    timeframe="1H",
                    limit=24,
                )
                if not isinstance(bars_response, Mapping):
                    return None
                bars_by_symbol = bars_response.get("bars")
                if not isinstance(bars_by_symbol, Mapping):
                    return None
                raw_bars = bars_by_symbol.get(resolved)
                response_receipt_id = _required_text(bars_response, "receipt_id")
                bars = _normalise_provider_bars(
                    raw_bars,
                    trusted_source_id=f"alpaca_crypto_bars_1h:{resolved}",
                    trusted_receipt_id=response_receipt_id,
                    max_latest_age=2 * 60 * 60,
                    max_history_age=MAX_HOURLY_HISTORY_AGE_SECONDS,
                )
                return _ticker_from_provider_bars(
                    bars,
                    source_id=bars[-1]["source_id"],
                )
        except Exception as e:
            logger.debug(f"Fetch ticker error {symbol}@{exchange}: {e}")
        return None
    
    async def _quick_momentum_check(
        self, 
        symbol: str, 
        exchange: str, 
        ticker_cache: Dict,
        cached: WaveAnalysis
    ) -> Optional[WaveAnalysis]:
        """Quick check if momentum has changed significantly."""
        if not self._analysis_has_fresh_provenance(cached):
            self._record_no_data(symbol, exchange, "stale_cached_wave_analysis")
            return None
        if not ticker_cache or symbol not in ticker_cache:
            return cached
        ticker = _normalise_ticker_receipt(ticker_cache[symbol])
        if ticker is None:
            self._record_no_data(
                symbol,
                exchange,
                "missing_stale_or_malformed_momentum_ticker",
            )
            return None
        
        new_change = ticker["change24h"]
        
        # Check for significant change (>1% difference)
        if abs(new_change - cached.change_24h) > 1.0:
            # Re-analyze
            return await self._analyze_wave(symbol, exchange, ticker_cache)
        
        return cached
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🌊 DEEP DIVE - Live Candle Analysis
    # ═══════════════════════════════════════════════════════════════════════
    
    async def deep_dive_candles(self, symbol: str, exchange: str) -> Dict:
        """
        Deep dive into live candles for a specific symbol.
        Analyzes candle patterns, volume, and micro-trends.
        """
        try:
            raw_candles = await self._fetch_candles(symbol, exchange, limit=30)
            candles = _normalise_provider_bars(raw_candles)
            if not candles or len(candles) < 10:
                denial = _no_data(
                    "missing_stale_malformed_or_insufficient_provider_bars",
                    symbol=symbol,
                    exchange=exchange,
                )
                self.last_no_data[symbol] = denial
                return denial
            
            # Analyze candle patterns
            patterns = self._detect_candle_patterns(candles)
            
            # Calculate micro-trends
            micro_trend = self._calculate_micro_trend(candles)
            
            # Volume analysis
            volume_profile = self._analyze_volume(candles)
            
            # RSI approximation
            rsi = self._calculate_rsi(candles)
            
            # Generate signal
            signal, confidence = self._generate_signal(patterns, micro_trend, volume_profile, rsi)
            latest = candles[-1]
            self.last_no_data.pop(symbol, None)
            return {
                "status": "ready",
                "data_status": "live",
                "truth_status": "real_derived",
                "symbol": symbol,
                "exchange": exchange,
                "candle_count": len(candles),
                "patterns": patterns,
                "micro_trend": micro_trend,
                "volume_profile": volume_profile,
                "rsi": rsi,
                "signal": signal,
                "confidence": confidence,
                "timestamp": latest["source_timestamp"],
                "source_id": latest["source_id"],
                "source_timestamp": latest["source_timestamp"],
                "received_at": latest["received_at"],
                "receipt_id": latest["receipt_id"],
                "generated_values": False,
                "eligible_for_action": True,
                "eligible_for_external_action": True,
                "eligible_for_accounting": False,
                "eligible_for_learning": True,
            }
            
        except Exception as e:
            logger.error(f"Deep dive error for {symbol}: {e}")
            denial = _no_data(
                "provider_bar_analysis_error",
                symbol=symbol,
                exchange=exchange,
            )
            self.last_no_data[symbol] = denial
            return denial
    
    async def _fetch_candles(
        self, 
        symbol: str, 
        exchange: str, 
        interval: str = '1m',
        limit: int = 30
    ) -> List[Dict]:
        """Fetch and normalise recent provider candles."""
        try:
            if exchange == 'kraken' and self.kraken and hasattr(self.kraken, "get_ohlc"):
                ohlc = self.kraken.get_ohlc(symbol, interval=1)  # 1 minute
                if isinstance(ohlc, Mapping) and 'result' in ohlc:
                    for key in ohlc['result']:
                        if key != 'last':
                            data = ohlc['result'][key]
                            raw_bars = [
                                {
                                    'timestamp': c[0],
                                    'open': c[1],
                                    'high': c[2],
                                    'low': c[3],
                                    'close': c[4],
                                    'volume': c[6],
                                }
                                for c in data[-limit:]
                            ]
                            return _normalise_provider_bars(
                                raw_bars,
                                trusted_source_id=f"kraken_ohlc_1m:{symbol}",
                                trusted_receipt_id=_required_text(ohlc, "receipt_id"),
                            )
            
            elif exchange == 'binance' and self.binance:
                klines = self.binance.get_klines(symbol=symbol, interval='1m', limit=limit)
                if isinstance(klines, list) and klines:
                    raw_bars = []
                    for kline in klines:
                        if isinstance(kline, Mapping):
                            raw_bars.append(dict(kline))
                        elif isinstance(kline, (list, tuple)) and len(kline) >= 6:
                            raw_bars.append(
                                {
                                    'timestamp': kline[0],
                                    'open': kline[1],
                                    'high': kline[2],
                                    'low': kline[3],
                                    'close': kline[4],
                                    'volume': kline[5],
                                }
                            )
                        else:
                            return []
                    return _normalise_provider_bars(
                        raw_bars,
                        trusted_source_id=f"binance_klines_1m:{symbol}",
                    )
            elif exchange == 'alpaca' and self.alpaca:
                resolved = symbol
                if hasattr(self.alpaca, "_resolve_symbol"):
                    resolved = self.alpaca._resolve_symbol(symbol)
                bars_response = self.alpaca.get_crypto_bars(
                    [resolved],
                    timeframe="1Min",
                    limit=limit,
                )
                if not isinstance(bars_response, Mapping):
                    return []
                bars_by_symbol = bars_response.get("bars")
                if not isinstance(bars_by_symbol, Mapping):
                    return []
                bars = bars_by_symbol.get(resolved)
                return _normalise_provider_bars(
                    bars,
                    trusted_source_id=f"alpaca_crypto_bars_1m:{resolved}",
                    trusted_receipt_id=_required_text(bars_response, "receipt_id"),
                )
        except Exception as e:
            logger.debug(f"Fetch candles error: {e}")
        
        return []
    
    def _detect_candle_patterns(self, candles: List[Dict]) -> List[Dict]:
        """Detect candlestick patterns in recent candles."""
        patterns = []
        
        if len(candles) < 3:
            return patterns
        
        for i in range(2, len(candles)):
            c = candles[i]      # Current
            p = candles[i-1]    # Previous
            pp = candles[i-2]   # Two back
            
            body = abs(c['close'] - c['open'])
            wick_upper = c['high'] - max(c['open'], c['close'])
            wick_lower = min(c['open'], c['close']) - c['low']
            
            # Bullish engulfing
            if (p['close'] < p['open'] and  # Previous bearish
                c['close'] > c['open'] and   # Current bullish
                c['close'] > p['open'] and
                c['open'] < p['close']):
                patterns.append({
                    'pattern': CandlePattern.BULLISH_ENGULF,
                    'index': i,
                    'confidence': 0.8
                })
            
            # Bearish engulfing
            elif (p['close'] > p['open'] and  # Previous bullish
                  c['close'] < c['open'] and   # Current bearish
                  c['close'] < p['open'] and
                  c['open'] > p['close']):
                patterns.append({
                    'pattern': CandlePattern.BEARISH_ENGULF,
                    'index': i,
                    'confidence': 0.8
                })
            
            # Hammer (bullish reversal)
            elif (wick_lower > body * 2 and
                  wick_upper < body * 0.3):
                patterns.append({
                    'pattern': CandlePattern.HAMMER,
                    'index': i,
                    'confidence': 0.7
                })
            
            # Doji (indecision)
            elif body < (c['high'] - c['low']) * 0.1:
                patterns.append({
                    'pattern': CandlePattern.DOJI,
                    'index': i,
                    'confidence': 0.5
                })
        
        return patterns
    
    def _calculate_micro_trend(self, candles: List[Dict]) -> Dict:
        """Calculate micro-trend from recent candles."""
        if len(candles) < 5:
            return {"direction": "NEUTRAL", "strength": 0.0}
        
        closes = [c['close'] for c in candles[-10:]]
        
        # Simple linear regression approximation
        n = len(closes)
        x_sum = sum(range(n))
        y_sum = sum(closes)
        xy_sum = sum(i * c for i, c in enumerate(closes))
        x2_sum = sum(i * i for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum) if (n * x2_sum - x_sum * x_sum) != 0 else 0
        
        # Normalize slope
        avg_price = y_sum / n if n > 0 else 1
        normalized_slope = (slope / avg_price) * 100  # Percent per candle
        
        if normalized_slope > 0.1:
            direction = "BULLISH"
        elif normalized_slope < -0.1:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"
        
        return {
            "direction": direction,
            "strength": min(1.0, abs(normalized_slope) / 0.5),
            "slope_pct": normalized_slope,
        }
    
    def _analyze_volume(self, candles: List[Dict]) -> Dict:
        """Analyze volume profile."""
        if not candles:
            return {"profile": "NEUTRAL", "ratio": 1.0}
        
        volumes = [c['volume'] for c in candles]
        avg_volume = sum(volumes) / len(volumes) if volumes else 1
        recent_volume = volumes[-1] if volumes else 0
        
        ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        if ratio > 2.0:
            profile = "SPIKE"
        elif ratio > 1.3:
            profile = "HIGH"
        elif ratio < 0.5:
            profile = "LOW"
        else:
            profile = "NORMAL"
        
        return {
            "profile": profile,
            "ratio": ratio,
            "avg": avg_volume,
            "current": recent_volume,
        }
    
    def _calculate_rsi(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate RSI from candles."""
        if len(candles) < period + 1:
            return 50.0
        
        changes = []
        for i in range(1, len(candles)):
            changes.append(candles[i]['close'] - candles[i-1]['close'])
        
        gains = [max(0, c) for c in changes[-period:]]
        losses = [abs(min(0, c)) for c in changes[-period:]]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _generate_signal(
        self, 
        patterns: List[Dict], 
        micro_trend: Dict, 
        volume_profile: Dict, 
        rsi: float
    ) -> Tuple[str, float]:
        """Generate trading signal from deep dive analysis."""
        
        bullish_score = 0.0
        bearish_score = 0.0
        
        # Pattern signals
        for p in patterns:
            if p['pattern'] in [CandlePattern.BULLISH_ENGULF, CandlePattern.HAMMER]:
                bullish_score += p['confidence'] * 0.3
            elif p['pattern'] in [CandlePattern.BEARISH_ENGULF]:
                bearish_score += p['confidence'] * 0.3
        
        # Trend signals
        if micro_trend['direction'] == 'BULLISH':
            bullish_score += micro_trend['strength'] * 0.25
        elif micro_trend['direction'] == 'BEARISH':
            bearish_score += micro_trend['strength'] * 0.25
        
        # Volume confirmation
        if volume_profile['profile'] == 'SPIKE':
            # Confirms the dominant direction
            if bullish_score > bearish_score:
                bullish_score *= 1.2
            else:
                bearish_score *= 1.2
        
        # RSI signals
        if rsi < 30:
            bullish_score += 0.2  # Oversold
        elif rsi > 70:
            bearish_score += 0.2  # Overbought
        
        # Generate signal
        if bullish_score > 0.5 and bullish_score > bearish_score * 1.3:
            return "🟢 BUY", min(1.0, bullish_score)
        elif bearish_score > 0.5 and bearish_score > bullish_score * 1.3:
            return "🔴 SELL", min(1.0, bearish_score)
        else:
            return "⚪ HOLD", max(bullish_score, bearish_score)
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 STATUS AND REPORTING
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_wave_allocation(self) -> Dict[str, Any]:
        """Get current wave allocation summary."""
        return {
            "total_scanned": self.total_symbols_scanned,
            "last_scan_time": self.last_full_scan_time,
            "wave_counts": {
                state.value: len(self.wave_buckets[state])
                for state in WaveState
            },
            "top_opportunities": [
                {
                    "symbol": opp.symbol,
                    "exchange": opp.exchange,
                    "wave": opp.wave_state.value,
                    "jump_score": opp.jump_score,
                    "change_24h": opp.change_24h,
                    "action": opp.action,
                }
                for opp in self.top_opportunities[:10]
            ],
            "universe_size": sum(len(s) for s in self.universe.values()),
        }
    
    def print_wave_report(self):
        """Print formatted wave report."""
        print("\n" + "=" * 70)
        print("🌊🔭 GLOBAL WAVE SCANNER - ALLOCATION REPORT")
        print("=" * 70)
        
        print(f"\n📊 UNIVERSE: {sum(len(s) for s in self.universe.values())} symbols")
        for ex, symbols in self.universe.items():
            print(f"   {ex.upper()}: {len(symbols)}")
        
        print(f"\n🌊 WAVE ALLOCATION:")
        for state in WaveState:
            count = len(self.wave_buckets[state])
            bar = "█" * min(50, count // 5)
            print(f"   {state.value:20} {count:5} {bar}")
        
        print(f"\n🎯 TOP OPPORTUNITIES:")
        for i, opp in enumerate(self.top_opportunities[:10], 1):
            print(f"   {i:2}. {opp.symbol:12} {opp.wave_state.value:15} "
                  f"Jump: {opp.jump_score:.2f} | 24h: {opp.change_24h:+.1f}%")
        
        print("=" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# 🐝 BEE SWEEP - Systematic A-Z/Z-A pollination
# ═══════════════════════════════════════════════════════════════════════════

async def run_bee_sweep(scanner: GlobalWaveScanner, ticker_cache: Dict = None):
    """
    🐝 BEE SWEEP: Systematic A-Z then Z-A coverage
    
    Like bees pollinating every flower, we scan EVERY symbol
    in alphabetical order, then reverse for confirmation.
    """
    print("\n🐝 STARTING BEE SWEEP - Full A-Z/Z-A Coverage...")
    
    # Build universe if not done
    if not scanner.sorted_symbols_az:
        await scanner.build_universe()
    
    # A-Z Sweep
    print("\n📊 PHASE 1: A-Z Sweep...")
    az_batches = await scanner.full_az_sweep(ticker_cache)
    
    # Z-A Sweep (confirmation)
    print("\n📊 PHASE 2: Z-A Sweep (confirmation)...")
    za_batches = await scanner.full_za_sweep(ticker_cache)
    
    # Print report
    scanner.print_wave_report()
    
    # Deep dive top opportunities
    print("\n🔬 PHASE 3: Deep Dive Top Waves...")
    for opp in scanner.top_opportunities[:5]:
        dive = await scanner.deep_dive_candles(opp.symbol, opp.exchange)
        if dive.get("status") == "no_data":
            print(f"   {opp.symbol}: NO_DATA ({dive.get('reason', 'provider evidence unavailable')})")
        else:
            print(f"   {opp.symbol}: {dive['signal']} "
                  f"(Conf: {dive['confidence']:.1%})")
    
    return {
        "az_batches": len(az_batches),
        "za_batches": len(za_batches),
        "top_opportunities": len(scanner.top_opportunities),
        "wave_allocation": scanner.get_wave_allocation(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 🧪 TEST / STANDALONE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    print("🌊🔭 AUREON GLOBAL WAVE SCANNER")
    print("=" * 50)
    
    # Create scanner (without exchange connections for test)
    scanner = GlobalWaveScanner()
    
    # Simulate some data
    scanner.universe = {
        'binance': {'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT'},
        'kraken': {'XBTUSD', 'ETHUSD'},
    }
    
    scanner.sorted_symbols_az = sorted([
        (s, ex) for ex, symbols in scanner.universe.items() for s in symbols
    ])
    scanner.sorted_symbols_za = list(reversed(scanner.sorted_symbols_az))
    
    print(f"Universe: {scanner.universe}")
    print(f"A-Z: {[s[0] for s in scanner.sorted_symbols_az]}")
    print(f"Z-A: {[s[0] for s in scanner.sorted_symbols_za]}")
    
    print("\n✅ Global Wave Scanner ready for integration!")
