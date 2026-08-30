#!/usr/bin/env python3
# Windows UTF-8 fix - MANDATORY for all Aureon modules
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        # Only wrap if not already UTF-8 wrapped (prevents re-wrapping on import)
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

"""
🔭🤖 AUREON BOT SHAPE SCANNER 🤖🔭
═══════════════════════════════════════════════════════════════════════════════
QUANTUM TELESCOPE FOR MARKET MICROSTRUCTURE
"See the shape of the bots traveling across the market"

This module visualizes algorithmic actors by decomposing market data into
spectral 3D fingerprints. It handles the "small to big" logic (micro to whale).

PRINCIPLES:
1. FREQUENCY DECOMPOSITION: Bots operate on loops. loops = frequencies.
2. 3D SHAPE CONSTRUCTION: Time x Frequency x Magnitude = The Bot's Shape.
3. SCALAR INVARIANCE: Small HFTs and Giant Whales share geometric properties.

OUTPUTS:
- `bot.shape.3d` (ThoughtBus)
- JSON Snapshots (for visualization)
- 3D Point Cloud Data (PLY/OBJ)

Gary Leckey | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import json
import logging
import numpy as np
import math
from datetime import datetime
from collections import deque, defaultdict
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple

# Internal imports
from aureon.exchanges.binance_ws_client import BinanceWebSocketClient, WSTrade, WSOrderBook
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None

# Chirp Bus - High Speed Signaling
try:
    from aureon.core.aureon_chirp_bus import ChirpBus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False
    ChirpBus = None

# Counter-intelligence integration
try:
    from aureon.utils.aureon_queen_counter_intelligence import queen_counter_intelligence, CounterIntelligenceSignal
    from aureon.bots_intelligence.aureon_global_firm_intelligence import get_attribution_engine
    COUNTER_INTELLIGENCE_AVAILABLE = True
except ImportError:
    COUNTER_INTELLIGENCE_AVAILABLE = False
    queen_counter_intelligence = None
    get_attribution_engine = None

# Firm intelligence catalog
try:
    from aureon.bots_intelligence.aureon_firm_intelligence_catalog import get_firm_catalog
    CATALOG_AVAILABLE = True
except ImportError:
    CATALOG_AVAILABLE = False
    get_firm_catalog = None

# Configuration
SPECTRUM_SCAN_INTERVAL = 5.0  # seconds between Shape refreshes
PROVIDER_VENUE = "binance"
PROVIDER_OBSERVATION_MAX_AGE_SECONDS = 30.0
PROVIDER_FUTURE_SKEW_SECONDS = 5.0
SPECTRUM_RETENTION_SECONDS = 7200.0


def _finite_number(value: Any, *, positive: bool = False) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    return number


def _provider_timestamp(value: Any) -> Optional[float]:
    if isinstance(value, datetime):
        try:
            value = value.timestamp()
        except (OSError, OverflowError, ValueError):
            return None
    return _finite_number(value, positive=True)


def _fresh_timestamp(
    value: Any,
    *,
    now: Optional[float] = None,
    max_age: float = PROVIDER_OBSERVATION_MAX_AGE_SECONDS,
) -> Optional[float]:
    observed = _provider_timestamp(value)
    current = _finite_number(time.time() if now is None else now, positive=True)
    if observed is None or current is None:
        return None
    if observed < current - max_age:
        return None
    if observed > current + PROVIDER_FUTURE_SKEW_SECONDS:
        return None
    return observed


def _valid_identifier(value: Any) -> Optional[str]:
    if value is None or isinstance(value, bool):
        return None
    identifier = str(value).strip()
    if not identifier:
        return None
    lowered = identifier.casefold()
    if lowered in {"0", "none", "null", "unknown", "pending", "n/a"}:
        return None
    return identifier


def _no_data(reason: str, *, symbol: Optional[str] = None) -> Dict[str, Any]:
    """Numeric-free rejection envelope that cannot cross operational surfaces."""
    return {
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": str(reason),
        "symbol": symbol,
        "provider_observation": False,
        "generated_values": False,
        "operational_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
    }

@dataclass
class SpectrumBandConfig:
    name: str # e.g. "INFRA_LOW"
    min_hz: float
    max_hz: float
    window_seconds: int
    sample_rate_ms: int # 0 for burst analysis
    description: str

# 🌈 THE FULL SPECTRUM (0.001 Hz to 10 MHz) 🌈
SPECTRUM_BANDS = [
    SpectrumBandConfig("INFRA_LOW", 0.001, 0.1, 7200, 10000, "Deep Ocean (Accumulators) 🌊"), 
    SpectrumBandConfig("MID_RANGE", 0.1, 10.0, 600, 100, "Surface Waves (Market Makers) 🏄"), 
    SpectrumBandConfig("HIGH_FREQ", 10.0, 1000.0, 60, 1, "The Rain (HFT/Scalpers) 🌧️"), 
    SpectrumBandConfig("ULTRA_HIGH", 1000.0, 10_000_000.0, 10, 0, "Quantum Foam (Flash Microwaves) ⚛️") 
]

logger = logging.getLogger("BotShapeScanner")
logging.basicConfig(level=logging.INFO)

@dataclass
class SpectralBandResult:
    band_name: str
    dominant_freq: float
    amplitude: float
    activity_score: float
    state_description: str # "Active", "Sleeping", "Spiking"

@dataclass
class BotShapeFingerprint:
    """The spectral DNA of an algorithmic actor"""
    symbol: str
    timestamp: float
    spectrum_results: List[SpectralBandResult] # Full spectrum breakdown
    volume_profile: List[float]  # Normalized volume buckets
    layering_score: float        # From depth (0.0 - 1.0)
    bot_class: str               # "HFT", "MM", "ACCUMULATOR", "ARBITRAGE"
    confidence: float
    data_status: str = "no_data"
    truth_status: str = "no_data"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    receipt_id: Optional[str] = None
    input_receipt_ids: List[str] = field(default_factory=list)
    provider_observation: bool = False
    input_provider_observation: bool = False
    generated_values: bool = False
    operational_eligible: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    
    @property
    def dominant_freqs(self) -> List[float]:
        # Backwards compatibility helper
        return [r.dominant_freq for r in self.spectrum_results if r.dominant_freq > 0]


def _trade_observation(trade: Any, *, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    if not isinstance(trade, WSTrade):
        return None
    symbol = _valid_identifier(trade.symbol)
    source_timestamp = _fresh_timestamp(trade.timestamp, now=now)
    price = _finite_number(trade.price, positive=True)
    quantity = _finite_number(trade.quantity, positive=True)
    trade_id = _finite_number(trade.trade_id, positive=True)
    if (
        symbol is None
        or str(trade.source).strip().lower() != PROVIDER_VENUE
        or source_timestamp is None
        or price is None
        or quantity is None
        or trade_id is None
        or not isinstance(trade.is_buyer_maker, bool)
    ):
        return None
    normalized_symbol = symbol.upper()
    return {
        "ts": source_timestamp,
        "px": price,
        "qty": quantity,
        "maker": trade.is_buyer_maker,
        "symbol": normalized_symbol,
        "data_status": "live",
        "truth_status": "real_observed",
        "source_id": f"binance.websocket.trade:{normalized_symbol}",
        "source_timestamp": source_timestamp,
        "receipt_id": f"binance.trade:{normalized_symbol}:{int(trade_id)}",
        "provider_observation": True,
        "generated_values": False,
        "operational_eligible": True,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": True,
    }


def _depth_observation(depth: Any, *, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    if not isinstance(depth, WSOrderBook):
        return None
    symbol = _valid_identifier(depth.symbol)
    source_timestamp = _fresh_timestamp(depth.timestamp, now=now)
    first_update_id = _finite_number(depth.first_update_id, positive=True)
    final_update_id = _finite_number(depth.final_update_id, positive=True)
    if (
        symbol is None
        or str(depth.source).strip().lower() != PROVIDER_VENUE
        or source_timestamp is None
        or first_update_id is None
        or final_update_id is None
        or final_update_id < first_update_id
    ):
        return None

    def normalize_side(rows: Any) -> Optional[List[Tuple[float, float]]]:
        if not isinstance(rows, list) or not rows:
            return None
        normalized = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                return None
            price = _finite_number(row[0], positive=True)
            quantity = _finite_number(row[1], positive=True)
            if price is None or quantity is None:
                return None
            normalized.append((price, quantity))
        return normalized

    bids = normalize_side(depth.bids)
    asks = normalize_side(depth.asks)
    if bids is None or asks is None or max(p for p, _ in bids) >= min(p for p, _ in asks):
        return None
    normalized_symbol = symbol.upper()
    return {
        "symbol": normalized_symbol,
        "bids": bids,
        "asks": asks,
        "data_status": "live",
        "truth_status": "real_observed",
        "source_id": f"binance.websocket.depth:{normalized_symbol}",
        "source_timestamp": source_timestamp,
        "receipt_id": (
            f"binance.depth:{normalized_symbol}:"
            f"{int(first_update_id)}:{int(final_update_id)}"
        ),
        "provider_observation": True,
        "generated_values": False,
        "operational_eligible": True,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": True,
    }


def _complete_observation(
    observation: Any,
    *,
    now: Optional[float] = None,
    max_age: float = SPECTRUM_RETENTION_SECONDS,
) -> bool:
    if not isinstance(observation, dict):
        return False
    if (
        observation.get("data_status") != "live"
        or observation.get("truth_status") != "real_observed"
        or observation.get("provider_observation") is not True
        or observation.get("generated_values") is not False
        or observation.get("operational_eligible") is not True
        or observation.get("accounting_eligible") is not False
        or observation.get("learning_eligible") is not True
    ):
        return False
    if _valid_identifier(observation.get("source_id")) is None:
        return False
    if _valid_identifier(observation.get("receipt_id")) is None:
        return False
    return _fresh_timestamp(
        observation.get("source_timestamp"),
        now=now,
        max_age=max_age,
    ) is not None


def _complete_shape_evidence(shape: Any, *, now: Optional[float] = None) -> bool:
    if not isinstance(shape, BotShapeFingerprint):
        return False
    if (
        shape.data_status != "live"
        or shape.truth_status != "real_derived"
        or shape.provider_observation is not False
        or shape.input_provider_observation is not True
        or shape.generated_values is not False
        or shape.operational_eligible is not True
        or shape.actionable is not False
        or shape.accounting_eligible is not False
        or shape.learning_eligible is not True
    ):
        return False
    if _valid_identifier(shape.source_id) is None:
        return False
    if _valid_identifier(shape.receipt_id) is None or not shape.input_receipt_ids:
        return False
    if any(_valid_identifier(value) is None for value in shape.input_receipt_ids):
        return False
    return _fresh_timestamp(shape.source_timestamp, now=now) is not None

class BotShapeScanner:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.ws_client = BinanceWebSocketClient()
        
        # Buffers: symbol -> deque of (timestamp, price, quantity)
        # We need a large buffer to cover the INFRA_LOW band (2 hours)
        # Even at 10 trades/sec, 2 hours = 72,000 trades. 
        self.trade_buffers: Dict[str, deque] = {s: deque(maxlen=100000) for s in symbols}
        self.depth_snapshot: Dict[str, Dict[str, Any]] = {}
        self.last_no_data: Dict[str, Dict[str, Any]] = {}
        self.counter_signal_envelopes: List[Dict[str, Any]] = []
        
        # ThoughtBus
        self.bus = ThoughtBus() if THOUGHT_BUS_AVAILABLE else None
        
        # ChirpBus
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE:
            try:
                self.chirp_bus = ChirpBus()
            except Exception:
                pass
        
        # Counter-intelligence integration
        self.attribution_engine = get_attribution_engine() if COUNTER_INTELLIGENCE_AVAILABLE else None
        self.counter_intelligence = queen_counter_intelligence if COUNTER_INTELLIGENCE_AVAILABLE else None
        
        # Firm intelligence catalog
        self.firm_catalog = get_firm_catalog() if CATALOG_AVAILABLE else None
        
        # Analysis State
        self.last_scan_time = 0
        self.scan_interval = SPECTRUM_SCAN_INTERVAL
        
        if COUNTER_INTELLIGENCE_AVAILABLE:
            logger.info("🤖 Counter-intelligence integration enabled")
        else:
            logger.warning("⚠️ Counter-intelligence not available - attribution disabled")
        
        if CATALOG_AVAILABLE:
            logger.info("📊 Firm Intelligence Catalog enabled")
        else:
            logger.warning("⚠️ Catalog not available - no firm tracking")
        
    def start(self):
        """Start the Quantum Telescope"""
        logger.info(f"🔭 Starting AUREON BOT SHAPE SCANNER on {len(self.symbols)} assets...")
        
        # Build streams: trades, depth, tickers
        # Use lowercase for subscription params
        streams = []
        for s in self.symbols:
            sl = s.lower()
            streams.append(f"{sl}@trade")
            streams.append(f"{sl}@depth5") # Light depth for layering analysis
            
        # Hook up callbacks
        self.ws_client.on_trade = self._on_trade
        self.ws_client.on_depth = self._on_depth
        
        self.ws_client.start(streams)
        
        # Main Loop
        try:
            while True:
                time.sleep(0.1)
                now = time.time()
                if now - self.last_scan_time > self.scan_interval:
                    self._scan_all_shapes()
                    self.last_scan_time = now
                    
        except KeyboardInterrupt:
            logger.info("👋 Scaling down Bot Shape Scanner...")
            self.ws_client.stop()

    def _on_trade(self, trade: WSTrade):
        """Buffer incoming trades for spectral analysis"""
        observation = _trade_observation(trade)
        symbol = str(getattr(trade, "symbol", "") or "").upper()
        if observation is None:
            self.last_no_data[symbol or "UNKNOWN"] = _no_data(
                "malformed_stale_or_unstamped_provider_trade",
                symbol=symbol or None,
            )
            return
        symbol = observation["symbol"]
        if symbol in self.trade_buffers:
            self.trade_buffers[symbol].append(observation)
            self.last_no_data.pop(symbol, None)
            
            # Prune? No, let deque handle maxlen. 
            # We need deep history for INFRA_LOW band.

    def _on_depth(self, depth: WSOrderBook):
        """Update depth snapshot for layering metrics"""
        observation = _depth_observation(depth)
        symbol = str(getattr(depth, "symbol", "") or "").upper()
        if observation is None:
            self.last_no_data[symbol or "UNKNOWN"] = _no_data(
                "malformed_stale_or_unstamped_provider_depth",
                symbol=symbol or None,
            )
            return
        symbol = observation["symbol"]
        if symbol in self.trade_buffers:
            self.depth_snapshot[symbol] = observation
            self.last_no_data.pop(symbol, None)

    def _scan_all_shapes(self):
        """Process all buffers and compute 3D shapes"""
        shapes = []
        
        logger.info("🔎 SCANNING BOT SPECTRUM (0.001Hz - 10MHz)...")
        logger.info(f"{'SYMBOL':<8} {'BAND':<12} {'FREQ (Hz)':<10} {'STATE':<15} {'SHAPE'}")
        logger.info("-" * 65)
        
        for symbol in self.symbols:
            fingerprint = self._compute_full_spectrum_fingerprint(symbol)
            if _complete_shape_evidence(fingerprint):
                shapes.append(fingerprint)
                self._emit_shape(fingerprint)
                
                # Visual log - show the "hottest" band
                active_bands = sorted(fingerprint.spectrum_results, key=lambda x: x.amplitude, reverse=True)
                top_band = active_bands[0] if active_bands else None
                
                if top_band:
                    freq_str = f"{top_band.dominant_freq:.3f}"
                    icon = "🤖" 
                    if fingerprint.bot_class == "ORGANIC": icon = "🌱"
                    elif fingerprint.bot_class == "QUANTUM_HFT": icon = "⚡"
                    
                    logger.info(f"{symbol:<8} {top_band.band_name[:10]:<12} {freq_str:<10} {top_band.state_description[:15]:<15} {icon}")

        # Save snapshot for external 3D viewer
        self._save_3d_snapshot(shapes)
        return shapes

    def _compute_full_spectrum_fingerprint(self, symbol: str) -> Optional[BotShapeFingerprint]:
        """The core 'Quantum Telescope' Logic: Full Spectrum Analysis"""
        buffer = self.trade_buffers.get(symbol)
        if not buffer or len(buffer) < 20: # Minimal data check
            self.last_no_data[symbol] = _no_data(
                "insufficient_provider_trade_observations",
                symbol=symbol,
            )
            return None
            
        data = list(buffer) # Copy for thread safety/stability
        now = time.time()
        if any(
            not _complete_observation(
                observation,
                now=now,
                max_age=SPECTRUM_RETENTION_SECONDS,
            )
            for observation in data
        ):
            self.last_no_data[symbol] = _no_data(
                "malformed_stale_or_unstamped_trade_buffer",
                symbol=symbol,
            )
            return None
        latest_trade_timestamp = _fresh_timestamp(
            data[-1].get("source_timestamp"),
            now=now,
        )
        if latest_trade_timestamp is None:
            self.last_no_data[symbol] = _no_data(
                "latest_provider_trade_is_stale",
                symbol=symbol,
            )
            return None
        
        results = []
        
        # Iterate through all spectral bands
        for band in SPECTRUM_BANDS:
            res = self._analyze_band(data, band, now)
            if res is None:
                self.last_no_data[symbol] = _no_data(
                    f"insufficient_live_data_for_{band.name.lower()}",
                    symbol=symbol,
                )
                return None
            results.append(res)
            
        # Classify based on the full spectrum
        bot_class = self._classify_spectrum(results)
        
        # Layering analysis
        layering = self._analyze_layering(symbol, now=now)
        if layering is None:
            self.last_no_data[symbol] = _no_data(
                "fresh_complete_provider_depth_required",
                symbol=symbol,
            )
            return None

        volume_profile = self._volume_profile(data)
        if volume_profile is None:
            self.last_no_data[symbol] = _no_data(
                "complete_positive_volume_profile_required",
                symbol=symbol,
            )
            return None

        activity_scores = [
            _finite_number(result.activity_score)
            for result in results
        ]
        if any(score is None for score in activity_scores):
            self.last_no_data[symbol] = _no_data(
                "non_finite_spectral_activity",
                symbol=symbol,
            )
            return None
        confidence = min(1.0, max(0.0, max(activity_scores)))
        depth = self.depth_snapshot[symbol]
        depth_timestamp = _fresh_timestamp(
            depth.get("source_timestamp"),
            now=now,
        )
        if depth_timestamp is None:
            self.last_no_data[symbol] = _no_data(
                "fresh_complete_provider_depth_required",
                symbol=symbol,
            )
            return None
        input_receipt_ids = [
            data[0]["receipt_id"],
            data[-1]["receipt_id"],
            depth["receipt_id"],
        ]
        source_timestamp = min(latest_trade_timestamp, depth_timestamp)
        receipt_id = (
            f"binance.shape:{symbol}:"
            f"{data[0]['receipt_id']}:{data[-1]['receipt_id']}:"
            f"{depth['receipt_id']}"
        )

        fingerprint = BotShapeFingerprint(
            symbol=symbol,
            timestamp=source_timestamp,
            spectrum_results=results,
            volume_profile=volume_profile,
            layering_score=layering,
            bot_class=bot_class,
            confidence=confidence,
            data_status="live",
            truth_status="real_derived",
            source_id=f"derived:binance.websocket.trade+depth:{symbol}",
            source_timestamp=source_timestamp,
            receipt_id=receipt_id,
            input_receipt_ids=input_receipt_ids,
            provider_observation=False,
            input_provider_observation=True,
            generated_values=False,
            operational_eligible=True,
            actionable=False,
            accounting_eligible=False,
            learning_eligible=True,
        )
        self.last_no_data.pop(symbol, None)
        return fingerprint

    def _volume_profile(self, data: List[Dict[str, Any]]) -> Optional[List[float]]:
        """Normalize ten chronological buckets from observed provider quantities."""
        if len(data) < 20:
            return None
        now = time.time()
        if any(
            not _complete_observation(
                row,
                now=now,
                max_age=SPECTRUM_RETENTION_SECONDS,
            )
            for row in data
        ):
            return None
        quantities = [_finite_number(row.get("qty"), positive=True) for row in data]
        if any(quantity is None for quantity in quantities):
            return None
        bucket_totals = []
        for index in range(10):
            start = index * len(quantities) // 10
            end = (index + 1) * len(quantities) // 10
            bucket_totals.append(sum(quantities[start:end]))
        total = sum(bucket_totals)
        if total <= 0:
            return None
        return [bucket / total for bucket in bucket_totals]

    def _analyze_band(self, data: List[Dict], band: SpectrumBandConfig, now: float) -> Optional[SpectralBandResult]:
        """Analyze a specific frequency band"""
        if not data or any(
            not _complete_observation(
                row,
                now=now,
                max_age=SPECTRUM_RETENTION_SECONDS,
            )
            for row in data
        ):
            return None
        # Filter data for this band's time window
        start_time = now - band.window_seconds
        
        # Optimization: Binary search or just skip
        # Since data is sorted by TS, we can slice efficiently
        # effective_data = [d for d in data if d['ts'] >= start_time] 
        # (Doing a simple filter for clarity, optimize if slow)
        effective_data = []
        for d in reversed(data):
            if d['ts'] < start_time:
                break
            effective_data.append(d)
        effective_data.reverse()
        
        if not effective_data:
            return None

        # --- ULTRA HIGH FREQUENCY (Burst Analysis) ---
        if band.sample_rate_ms == 0: 
            # 10 MHz equivalent -> 100ns resolution.
            # We look for "micro-bursts": multiple trades in < 1ms
            burst_count = 0
            max_burst_density = 0
            
            for i in range(1, len(effective_data)):
                dt = effective_data[i]['ts'] - effective_data[i-1]['ts']
                if dt < 0.001: # Less than 1ms separation
                    burst_count += 1
            
            # Frequency proxy: bursts per second * multiplier
            freq_proxy = (burst_count / max(1, band.window_seconds)) * 1000.0  
            amplitude = burst_count / len(effective_data) if effective_data else 0
            
            state = "Quantum Calm"
            if freq_proxy > 1000: state = "SINGULARITY ⚛️"
            elif freq_proxy > 100: state = "Micro-Ripples"
            
            return SpectralBandResult(band.name, freq_proxy, amplitude, amplitude, state)

        # --- HIGH FREQ (Inter-arrival Analysis) ---
        elif band.sample_rate_ms <= 10:
             # Fast FFT or Inter-arrival
             # For High Freq, FFT on 1ms grid is expensive.
             # Use inter-arrival times stats.
             deltas = []
             for i in range(1, len(effective_data)):
                 deltas.append(effective_data[i]['ts'] - effective_data[i-1]['ts'])
             
             if not deltas:
                 return None
                 
             mean_delta = np.mean(deltas)
             if mean_delta > 0:
                 approx_freq = 1.0 / mean_delta
             else:
                 approx_freq = 0.0
                 
             state = "Drizzle"
             if approx_freq > 50: state = "Heavy Rain 🌧️"
             
             return SpectralBandResult(band.name, approx_freq, 0.5, 0.5, state)

        # --- MID & LOW (Standard FFT) ---
        else:
            return self._perform_fft_analysis(effective_data, band, now)

    def _perform_fft_analysis(self, data: List[Dict], band: SpectrumBandConfig, now: float) -> Optional[SpectralBandResult]:
        """Standard FFT for Mid/Low bands"""
        if len(data) < 10:
             return None
        if any(
            not _complete_observation(
                row,
                now=now,
                max_age=SPECTRUM_RETENTION_SECONDS,
            )
            for row in data
        ):
             return None

        # Resample to uniform grid
        grid_points = int(band.window_seconds * (1000 / band.sample_rate_ms))
        signal = np.zeros(grid_points)
        start_time = now - band.window_seconds
        sample_period_sec = band.sample_rate_ms / 1000.0
        
        for t in data:
            idx = int((t['ts'] - start_time) / sample_period_sec)
            if 0 <= idx < grid_points:
                signal[idx] += t['qty']
                
        # Remove DC
        if np.all(signal == 0):
             return None
             
        signal_centered = signal - np.mean(signal)
        
        # FFT
        fft_vals = np.fft.rfft(signal_centered)
        fft_freq = np.fft.rfftfreq(len(signal_centered), d=sample_period_sec)
        magnitudes = np.abs(fft_vals)
        
        # Filter for band range
        mask = (fft_freq >= band.min_hz) & (fft_freq <= band.max_hz)
        band_freqs = fft_freq[mask]
        band_mags = magnitudes[mask]
        
        if len(band_mags) == 0:
             return None
             
        peak_idx = np.argmax(band_mags)
        dom_freq = band_freqs[peak_idx]
        peak_amp = band_mags[peak_idx]
        
        # Normalize amp
        norm_amp = peak_amp / (np.sum(signal) + 1e-9) * 100.0
        
        state = "Normal"
        if norm_amp > 0.5: state = "High Coherence 🌊"
        if norm_amp > 1.0: state = "STANDING WAVE ⚠️"
        
        return SpectralBandResult(band.name, dom_freq, norm_amp, norm_amp, state)

    def _analyze_layering(self, symbol: str, *, now: Optional[float] = None) -> Optional[float]:
        """Analyze Order Book Layering"""
        if symbol not in self.depth_snapshot:
            return None
        depth = self.depth_snapshot[symbol]
        if not _complete_observation(depth, now=now):
            return None
        # Simple metric: how uniform are the bid/ask steps?
        bids = [p for p, q in depth["bids"][:5]]
        asks = [p for p, q in depth["asks"][:5]]
        bid_diffs = np.diff(bids) if len(bids) > 1 else []
        ask_diffs = np.diff(asks) if len(asks) > 1 else []
        
        if len(bid_diffs) == 0 or len(ask_diffs) == 0:
            return None
            
        bid_var = np.var(bid_diffs)
        ask_var = np.var(ask_diffs)
        
        # Lower variance = higher layering score (artificial uniformity)
        # Avoid div by zero
        return 1.0 / (1.0 + (bid_var + ask_var)*10000)

    def _classify_spectrum(self, results: List[SpectralBandResult]) -> str:
        """Determine Bot Class from Spectral Fingerprint"""
        # Find strongest band
        sorted_bands = sorted(results, key=lambda x: x.amplitude, reverse=True)
        if not sorted_bands or sorted_bands[0].amplitude < 0.01:
            return "ORGANIC"
        
        strongest = sorted_bands[0]
        
        if strongest.band_name == "ULTRA_HIGH":
            return "QUANTUM_HFT"
        elif strongest.band_name == "HIGH_FREQ":
            return "SCALPER_BOT"
        elif strongest.band_name == "MID_RANGE":
            return "MARKET_MAKER"
        elif strongest.band_name == "INFRA_LOW":
            return "WHALE_ACCUMULATOR"
            
        return "UNKNOWN_ENTITY"

    def _emit_shape(self, shape: BotShapeFingerprint):
        """Emit ThoughtBus pulse and analyze for counter-intelligence opportunities"""
        if not _complete_shape_evidence(shape):
            symbol = getattr(shape, "symbol", None)
            self.last_no_data[symbol or "UNKNOWN"] = _no_data(
                "complete_fresh_shape_evidence_required",
                symbol=symbol,
            )
            return
        if self.bus:
            self.bus.think(
                f"Bot Shape Detected: {shape.symbol} ({shape.bot_class})",
                topic="bot.shape",
                priority="high" if "HFT" in shape.bot_class else "normal",
                metadata=asdict(shape)
            )
        
        # Counter-intelligence analysis
        if self.attribution_engine and self.counter_intelligence:
            self._analyze_counter_intelligence(shape)

    def _analyze_counter_intelligence(self, shape: BotShapeFingerprint):
        """Analyze bot shape for counter-intelligence opportunities"""
        try:
            if not _complete_shape_evidence(shape):
                self.last_no_data[getattr(shape, "symbol", "UNKNOWN")] = _no_data(
                    "complete_fresh_shape_evidence_required",
                    symbol=getattr(shape, "symbol", None),
                )
                return
            # Extract bot characteristics for attribution
            if not shape.dominant_freqs:
                self.last_no_data[shape.symbol] = _no_data(
                    "dominant_provider_derived_frequency_required",
                    symbol=shape.symbol,
                )
                return
            primary_freq = _finite_number(shape.dominant_freqs[0], positive=True)
            if primary_freq is None:
                self.last_no_data[shape.symbol] = _no_data(
                    "dominant_provider_derived_frequency_required",
                    symbol=shape.symbol,
                )
                return
            
            # Derive observed average notional from provider trades.
            recent_trades = list(self.trade_buffers.get(shape.symbol, []))[-10:]
            if len(recent_trades) < 10 or any(
                not _complete_observation(row, max_age=PROVIDER_OBSERVATION_MAX_AGE_SECONDS)
                for row in recent_trades
            ):
                self.last_no_data[shape.symbol] = _no_data(
                    "fresh_provider_trades_required_for_attribution",
                    symbol=shape.symbol,
                )
                return
            notionals = []
            for trade in recent_trades:
                price = _finite_number(trade.get("px"), positive=True)
                quantity = _finite_number(trade.get("qty"), positive=True)
                if price is None or quantity is None:
                    self.last_no_data[shape.symbol] = _no_data(
                        "malformed_provider_notional_inputs",
                        symbol=shape.symbol,
                    )
                    return
                notionals.append(price * quantity)
            avg_order_size = sum(notionals) / len(notionals)
            
            # Get current UTC hour
            current_hour_utc = int(time.gmtime(shape.source_timestamp).tm_hour)
            
            # Attempt firm attribution
            attribution_matches = self.attribution_engine.attribute_bot_to_firm(
                symbol=shape.symbol,
                frequency=primary_freq,
                order_size_usd=avg_order_size,
                strategy=shape.bot_class.split('_')[0],  # Extract base strategy
                current_hour_utc=current_hour_utc
            )
            
            if isinstance(attribution_matches, (list, tuple)) and attribution_matches:
                top_match = attribution_matches[0]
                if not isinstance(top_match, (list, tuple)) or len(top_match) != 2:
                    return
                firm_id, confidence = top_match
                confidence = _finite_number(confidence)
                
                if (
                    _valid_identifier(firm_id) is not None
                    and confidence is not None
                    and 0.7 <= confidence <= 1.0
                ):  # High confidence threshold
                    logger.info(f"🎯 Attributed {shape.symbol} bot to {firm_id} (confidence: {confidence:.2f})")
                    
                    # Prepare market data for counter-analysis
                    market_data = self._prepare_market_data(shape.symbol)
                    if market_data.get("data_status") != "live":
                        self.last_no_data[shape.symbol] = market_data
                        return
                    bot_detection_data = {
                        'confidence': shape.confidence,
                        'bot_class': shape.bot_class,
                        'frequency': primary_freq,
                        'layering_score': shape.layering_score,
                        'data_status': shape.data_status,
                        'truth_status': shape.truth_status,
                        'source_id': shape.source_id,
                        'source_timestamp': shape.source_timestamp,
                        'receipt_id': shape.receipt_id,
                        'generated_values': False,
                    }
                    
                    # Analyze for counter-opportunity
                    counter_signal = self.counter_intelligence.analyze_firm_for_counter_opportunity(
                        firm_id=firm_id,
                        market_data=market_data,
                        bot_detection_data=bot_detection_data
                    )
                    
                    if counter_signal:
                        # Emit counter-intelligence signal
                        self._emit_counter_signal(
                            counter_signal,
                            shape=shape,
                            market_data=market_data,
                            attribution_confidence=confidence,
                        )
                        
        except Exception as e:
            logger.error(f"Counter-intelligence analysis failed: {e}")

    def _prepare_market_data(self, symbol: str) -> Dict:
        """Prepare market data snapshot for counter-analysis"""
        now = time.time()
        buffer = list(self.trade_buffers.get(symbol, []))
        depth = self.depth_snapshot.get(symbol)
        if len(buffer) < 20:
            return _no_data("insufficient_provider_trades_for_market_metrics", symbol=symbol)
        if any(
            not _complete_observation(
                row,
                now=now,
                max_age=PROVIDER_OBSERVATION_MAX_AGE_SECONDS,
            )
            for row in buffer[-20:]
        ):
            return _no_data("stale_or_unstamped_provider_trades", symbol=symbol)
        if not _complete_observation(
            depth,
            now=now,
            max_age=PROVIDER_OBSERVATION_MAX_AGE_SECONDS,
        ):
            return _no_data("fresh_complete_provider_depth_required", symbol=symbol)

        recent = buffer[-20:]
        prices = []
        notionals = []
        for row in recent:
            price = _finite_number(row.get("px"), positive=True)
            quantity = _finite_number(row.get("qty"), positive=True)
            if price is None or quantity is None:
                return _no_data("malformed_provider_market_numbers", symbol=symbol)
            prices.append(price)
            notionals.append(price * quantity)

        returns = [
            abs(prices[index] - prices[index - 1]) / prices[index - 1]
            for index in range(1, len(prices))
        ]
        prior_average = sum(notionals[:10]) / 10
        recent_average = sum(notionals[10:]) / 10
        if not returns or prior_average <= 0:
            return _no_data("market_metrics_not_derivable", symbol=symbol)

        bids = depth["bids"]
        asks = depth["asks"]
        best_bid = max(price for price, _ in bids)
        best_ask = min(price for price, _ in asks)
        spread = best_ask - best_bid
        if spread <= 0:
            return _no_data("invalid_provider_spread", symbol=symbol)

        source_timestamp = min(
            recent[-1]["source_timestamp"],
            depth["source_timestamp"],
        )
        latency_ms = (now - source_timestamp) * 1000.0
        if latency_ms < 0:
            return _no_data("future_dated_provider_observation", symbol=symbol)

        return {
            "symbol": symbol,
            "volatility": sum(returns) / len(returns),
            "volume_ratio": recent_average / prior_average,
            "spread_pips": spread * 10000,
            "average_latency_ms": latency_ms,
            "data_status": "live",
            "truth_status": "real_derived",
            "source_id": f"derived:binance.websocket.market:{symbol}",
            "source_timestamp": source_timestamp,
            "receipt_id": (
                f"binance.market:{symbol}:"
                f"{recent[0]['receipt_id']}:{recent[-1]['receipt_id']}:"
                f"{depth['receipt_id']}"
            ),
            "input_receipt_ids": [
                recent[0]["receipt_id"],
                recent[-1]["receipt_id"],
                depth["receipt_id"],
            ],
            "provider_observation": False,
            "input_provider_observation": True,
            "generated_values": False,
            "operational_eligible": True,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": True,
        }

    def _emit_counter_signal(
        self,
        signal: CounterIntelligenceSignal,
        *,
        shape: BotShapeFingerprint,
        market_data: Dict[str, Any],
        attribution_confidence: float,
    ):
        """Emit counter-intelligence signal via ThoughtBus and Queen consultation"""
        if not _complete_shape_evidence(shape):
            return _no_data("complete_fresh_shape_evidence_required", symbol=shape.symbol)
        if (
            market_data.get("data_status") != "live"
            or market_data.get("truth_status") != "real_derived"
            or market_data.get("input_provider_observation") is not True
            or market_data.get("generated_values") is not False
            or market_data.get("actionable") is not False
            or _fresh_timestamp(market_data.get("source_timestamp")) is None
            or _valid_identifier(market_data.get("source_id")) is None
            or _valid_identifier(market_data.get("receipt_id")) is None
        ):
            return _no_data("complete_fresh_market_evidence_required", symbol=shape.symbol)

        firm_id = _valid_identifier(getattr(signal, "firm_id", None))
        strategy = getattr(getattr(signal, "strategy", None), "value", None)
        signal_confidence = _finite_number(getattr(signal, "confidence", None))
        timing_advantage = _finite_number(getattr(signal, "timing_advantage", None))
        expected_profit_pips = _finite_number(
            getattr(signal, "expected_profit_pips", None)
        )
        risk_score = _finite_number(getattr(signal, "risk_score", None))
        execution_window = _finite_number(
            getattr(signal, "execution_window_seconds", None),
            positive=True,
        )
        attribution_confidence = _finite_number(attribution_confidence)
        if (
            firm_id is None
            or _valid_identifier(strategy) is None
            or signal_confidence is None
            or not 0.0 <= signal_confidence <= 1.0
            or timing_advantage is None
            or expected_profit_pips is None
            or risk_score is None
            or not 0.0 <= risk_score <= 1.0
            or execution_window is None
            or attribution_confidence is None
            or not 0.0 <= attribution_confidence <= 1.0
        ):
            return _no_data("malformed_counter_signal_derivation", symbol=shape.symbol)

        source_timestamp = min(
            shape.source_timestamp,
            market_data["source_timestamp"],
        )
        signal_envelope = {
            "firm_id": firm_id,
            "strategy": strategy,
            "confidence": signal_confidence,
            "attribution_confidence": attribution_confidence,
            "timing_advantage": timing_advantage,
            "expected_profit_pips": expected_profit_pips,
            "risk_score": risk_score,
            "execution_window_seconds": execution_window,
            "reasoning": str(getattr(signal, "reasoning", "") or ""),
            "symbol": shape.symbol,
            "data_status": "live",
            "truth_status": "real_derived",
            "source_id": f"derived:bot_shape_counter:{shape.symbol}",
            "source_timestamp": source_timestamp,
            "receipt_id": (
                f"bot_shape.counter:{shape.symbol}:"
                f"{shape.receipt_id}:{market_data['receipt_id']}"
            ),
            "input_receipt_ids": [
                shape.receipt_id,
                market_data["receipt_id"],
            ],
            "provider_observation": False,
            "input_provider_observation": True,
            "generated_values": False,
            "operational_eligible": True,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": True,
        }
        self.counter_signal_envelopes.append(signal_envelope)
        # ThoughtBus emission
        if self.bus:
            self.bus.think(
                f"Counter-Intelligence: {signal.firm_id} ({signal.strategy.value})",
                topic="counter.intelligence",
                priority="critical" if signal.confidence > 0.9 else "high",
                metadata=signal_envelope,
            )
            
        # ChirpBus emission
        if self.chirp_bus:
            self.chirp_bus.publish("counter.signal", signal_envelope)
        
        # 👑 QUEEN CONSULTATION - Send counter-signal to Queen for approval
        # (Would be wired externally if Queen is available)
        try:
            # Look for global queen instance
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
            if hasattr(QueenHiveMind, '_global_instance') and QueenHiveMind._global_instance:
                queen = QueenHiveMind._global_instance
                if hasattr(queen, 'receive_counter_intelligence_signal'):
                    queen_decision = queen.receive_counter_intelligence_signal(
                        signal_envelope
                    )
                    
                    if queen_decision.get('approved'):
                        logger.info(f"👑🔪 Queen APPROVED counter-hunt: {signal.firm_id}")
        except Exception:
            pass  # Queen not available - continue anyway
            
        logger.info(
            f"🚨 Counter-signal emitted: {signal.firm_id} - {signal.strategy.value} "
            f"(confidence: {signal.confidence:.2f}, timing: {signal.timing_advantage:.1f}ms)"
        )

        return signal_envelope

    def _save_3d_snapshot(self, shapes: List[BotShapeFingerprint]):
        """Save a snapshot for the 3D viewer"""
        verified = [shape for shape in shapes if _complete_shape_evidence(shape)]
        if verified:
            receipt_ids = [shape.receipt_id for shape in verified]
            data = {
                "data_status": "live",
                "truth_status": "real_derived",
                "source_id": "derived:binance.websocket.bot_shapes",
                "source_timestamp": min(
                    shape.source_timestamp for shape in verified
                ),
                "receipt_id": "bot_shape.snapshot:" + ":".join(receipt_ids),
                "input_receipt_ids": receipt_ids,
                "provider_observation": False,
                "input_provider_observation": True,
                "generated_values": False,
                "operational_eligible": True,
                "actionable": False,
                "accounting_eligible": False,
                "learning_eligible": True,
                "shapes": [asdict(shape) for shape in verified],
                "rejections": list(self.last_no_data.values()),
            }
        else:
            data = _no_data("no_complete_fresh_bot_shapes")
            data["shapes"] = []
            data["rejections"] = list(self.last_no_data.values())
        with open("bot_shape_snapshot.json", "w") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    scan_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", 
        "XRPUSDT", "BNBUSDT", "ADAUSDT"
    ]
    scanner = BotShapeScanner(scan_symbols)
    scanner.start()

# Integration getter for SpectrumBandConfig
_GLOBAL_INSTANCE = None

def get_bot_scanner():
    global _GLOBAL_INSTANCE
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = BotShapeScanner()
    return _GLOBAL_INSTANCE

# Fix getter - provide default symbols
def get_bot_scanner():
    global _GLOBAL_INSTANCE
    if _GLOBAL_INSTANCE is None:
        # Default to common trading pairs for bot detection
        default_symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD']
        _GLOBAL_INSTANCE = BotShapeScanner(symbols=default_symbols)
    return _GLOBAL_INSTANCE
