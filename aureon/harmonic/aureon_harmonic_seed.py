#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🌊 AUREON HARMONIC WAVE SEED 🌊                                                  ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     Historical Seed Loader for Harmonic Wave Fusion                                  ║
║                                                                                      ║
║     ARCHITECTURE:                                                                    ║
║       • Fetch 7-day OHLCV history for full symbol universe                          ║
║       • Build initial wave state (phase, amplitude, frequency)                       ║
║       • Calculate cross-symbol coherence matrix                                      ║
║       • Serialize for fast restart                                                   ║
║                                                                                      ║
║     Like a 3D printer: historical data = initial form                               ║
║     Live ticks add layers, pattern system watches evolution                         ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import math
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════# 👑💰 QUEEN'S SACRED 1.88% LAW - SOURCE LAW DIRECT! 💰👑
# ═════════════════════════════════════════════════════════════
#
#   THE QUEEN COMMANDS: MIN_COP = 1.0188 (1.88% MINIMUM REALIZED PROFIT)
#   The seed grows only toward profitable branches!
#
# ═════════════════════════════════════════════════════════════

QUEEN_MIN_COP = 1.0188               # 👑 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88          # 👑 The sacred number as percentage
QUEEN_PROFIT_THRESHOLD = 0.0188      # 👑 As decimal multiplier

# ═════════════════════════════════════════════════════════════# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════

PHI = 1.618033988749895
SCHUMANN_BASE = 7.83  # Hz - Earth's heartbeat
LOVE_FREQ = 528  # Hz - Transformation frequency
SOLFEGGIO = [174, 285, 396, 417, 528, 639, 741, 852, 963]

# Timeframe constants
SEED_DAYS = 7
CANDLE_INTERVAL_HOURS = 1  # 1-hour candles
CANDLES_PER_DAY = 24
SEED_CANDLE_COUNT = SEED_DAYS * CANDLES_PER_DAY  # 168 candles
MAX_HARMONIC_CACHE_BYTES = 32 * 1024 * 1024
MAX_HARMONIC_SYMBOLS = 10_000
MAX_HARMONIC_HISTORY_VALUES = 2_048
MAX_COHERENCE_VALUES = 1_000_000


def _finite_number(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or type(value) not in {int, float}:
        raise ValueError(f"{field_name}_must_be_finite_number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name}_must_be_finite_number")
    return result


def _bounded_number_list(value: Any, *, field_name: str) -> List[float]:
    if not isinstance(value, list) or len(value) > MAX_HARMONIC_HISTORY_VALUES:
        raise ValueError(f"{field_name}_invalid")
    return [
        _finite_number(item, field_name=field_name)
        for item in value
    ]


def _decode_harmonic_cache(raw: bytes) -> Dict[str, Any]:
    """Decode exact canonical JSON while rejecting duplicates and NaN values."""

    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_HARMONIC_CACHE_BYTES:
        raise ValueError("harmonic_seed_cache_size_invalid")

    def reject_duplicates(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("harmonic_seed_cache_duplicate_key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> Any:
        raise ValueError("harmonic_seed_cache_non_finite_number")

    try:
        text = raw.decode("utf-8", errors="strict")
        decoded = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
        canonical = json.dumps(
            decoded,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (UnicodeDecodeError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("harmonic_seed_cache_json_invalid") from exc
    if canonical != raw or not isinstance(decoded, dict):
        raise ValueError("harmonic_seed_cache_not_canonical")
    return decoded


@dataclass
class SymbolWaveState:
    """Wave state for a single symbol"""
    symbol: str
    phase: float = 0.0  # Current phase (0 to 2π)
    amplitude: float = 0.0  # Wave amplitude (volatility proxy)
    frequency: float = 0.0  # Dominant frequency
    velocity: float = 0.0  # Rate of change
    coherence: float = 0.0  # Self-coherence score
    last_price: float = 0.0
    last_volume: float = 0.0
    last_update: float = 0.0
    price_history: List[float] = field(default_factory=list)
    volume_history: List[float] = field(default_factory=list)
    phase_history: List[float] = field(default_factory=list)
    

@dataclass
class GlobalHarmonicState:
    """The evolving 3D harmonic model"""
    symbols: Dict[str, SymbolWaveState] = field(default_factory=dict)
    coherence_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    global_phase: float = 0.0
    global_coherence: float = 0.0
    dominant_frequency: float = SCHUMANN_BASE
    schumann_alignment: float = 0.0
    market_regime: str = "neutral"
    last_update: float = 0.0
    candle_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict"""
        return {
            "symbols": {k: asdict(v) for k, v in self.symbols.items()},
            "coherence_matrix": self.coherence_matrix,
            "global_phase": self.global_phase,
            "global_coherence": self.global_coherence,
            "dominant_frequency": self.dominant_frequency,
            "schumann_alignment": self.schumann_alignment,
            "market_regime": self.market_regime,
            "last_update": self.last_update,
            "candle_count": self.candle_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalHarmonicState":
        """Reconstruct one exact, bounded, non-executable cache schema."""

        expected_state_fields = {
            "symbols",
            "coherence_matrix",
            "global_phase",
            "global_coherence",
            "dominant_frequency",
            "schumann_alignment",
            "market_regime",
            "last_update",
            "candle_count",
        }
        symbol_fields = {
            "symbol",
            "phase",
            "amplitude",
            "frequency",
            "velocity",
            "coherence",
            "last_price",
            "last_volume",
            "last_update",
            "price_history",
            "volume_history",
            "phase_history",
        }
        if not isinstance(data, dict) or set(data) != expected_state_fields:
            raise ValueError("harmonic_seed_cache_schema_invalid")
        raw_symbols = data["symbols"]
        if not isinstance(raw_symbols, dict) or len(raw_symbols) > MAX_HARMONIC_SYMBOLS:
            raise ValueError("harmonic_seed_symbols_invalid")
        state = cls()
        for key, raw_state in raw_symbols.items():
            if (
                not isinstance(key, str)
                or not key
                or len(key.encode("utf-8")) > 128
                or not isinstance(raw_state, dict)
                or set(raw_state) != symbol_fields
                or raw_state.get("symbol") != key
            ):
                raise ValueError("harmonic_seed_symbol_schema_invalid")
            normalized = {
                "symbol": key,
                **{
                    field_name: _finite_number(raw_state[field_name], field_name=field_name)
                    for field_name in (
                        "phase",
                        "amplitude",
                        "frequency",
                        "velocity",
                        "coherence",
                        "last_price",
                        "last_volume",
                        "last_update",
                    )
                },
                **{
                    field_name: _bounded_number_list(
                        raw_state[field_name],
                        field_name=field_name,
                    )
                    for field_name in (
                        "price_history",
                        "volume_history",
                        "phase_history",
                    )
                },
            }
            state.symbols[key] = SymbolWaveState(**normalized)

        raw_matrix = data["coherence_matrix"]
        if not isinstance(raw_matrix, dict) or len(raw_matrix) > MAX_HARMONIC_SYMBOLS:
            raise ValueError("harmonic_seed_coherence_matrix_invalid")
        coherence_matrix: Dict[str, Dict[str, float]] = {}
        coherence_values = 0
        for row_name, raw_row in raw_matrix.items():
            if (
                not isinstance(row_name, str)
                or row_name not in state.symbols
                or not isinstance(raw_row, dict)
                or len(raw_row) > MAX_HARMONIC_SYMBOLS
            ):
                raise ValueError("harmonic_seed_coherence_row_invalid")
            coherence_values += len(raw_row)
            if coherence_values > MAX_COHERENCE_VALUES:
                raise ValueError("harmonic_seed_coherence_limit_exceeded")
            row: Dict[str, float] = {}
            for column_name, raw_value in raw_row.items():
                if not isinstance(column_name, str) or column_name not in state.symbols:
                    raise ValueError("harmonic_seed_coherence_column_invalid")
                row[column_name] = _finite_number(
                    raw_value,
                    field_name="coherence_matrix_value",
                )
            coherence_matrix[row_name] = row
        state.coherence_matrix = coherence_matrix
        state.global_phase = _finite_number(data["global_phase"], field_name="global_phase")
        state.global_coherence = _finite_number(
            data["global_coherence"],
            field_name="global_coherence",
        )
        state.dominant_frequency = _finite_number(
            data["dominant_frequency"],
            field_name="dominant_frequency",
        )
        state.schumann_alignment = _finite_number(
            data["schumann_alignment"],
            field_name="schumann_alignment",
        )
        regime = data["market_regime"]
        if not isinstance(regime, str) or not regime or len(regime.encode("utf-8")) > 128:
            raise ValueError("harmonic_seed_market_regime_invalid")
        state.market_regime = regime
        state.last_update = _finite_number(data["last_update"], field_name="last_update")
        candle_count = data["candle_count"]
        if type(candle_count) is not int or not 0 <= candle_count <= 1_000_000_000:
            raise ValueError("harmonic_seed_candle_count_invalid")
        state.candle_count = candle_count
        return state


class HarmonicSeedLoader:
    """
    Loads 7-day historical data and builds the initial harmonic wave seed.
    This is the "initial form" that live data will grow upon.
    """
    
    def __init__(self, cache_dir: str = "harmonic_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.state = GlobalHarmonicState()
        self._exchange_clients = {}
        
    def _get_clients(self):
        """Lazy-load exchange clients"""
        if not self._exchange_clients:
            try:
                from aureon.exchanges.kraken_client import get_kraken_client
                self._exchange_clients['kraken'] = get_kraken_client()
                logger.info("✅ Kraken client initialized")
            except Exception as e:
                logger.warning(f"Could not init Kraken: {e}")
            
            try:
                from aureon.exchanges.binance_client import BinanceClient
                self._exchange_clients['binance'] = BinanceClient()
                logger.info("✅ Binance client initialized")
            except Exception as e:
                logger.warning(f"Could not init Binance: {e}")
                
        return self._exchange_clients
    
    def discover_universe(self) -> List[Tuple[str, str]]:
        """
        Dynamically discover all available symbols across exchanges.
        Returns list of (symbol, exchange) tuples.
        """
        universe = []
        clients = self._get_clients()
        
        # Kraken symbols
        if 'kraken' in clients:
            try:
                kraken = clients['kraken']
                pairs = kraken.get_tradable_pairs() if hasattr(kraken, 'get_tradable_pairs') else {}
                if not pairs:
                    # Fallback: get from tickers
                    tickers = kraken.get_24h_tickers() if hasattr(kraken, 'get_24h_tickers') else []
                    for t in tickers:
                        sym = t.get('symbol', '')
                        if sym:
                            universe.append((sym, 'kraken'))
                else:
                    for pair in pairs.keys():
                        universe.append((pair, 'kraken'))
                logger.info(f"🔍 Kraken: discovered {len([u for u in universe if u[1]=='kraken'])} symbols")
            except Exception as e:
                logger.warning(f"Kraken discovery failed: {e}")
        
        # Binance symbols
        if 'binance' in clients:
            try:
                binance = clients['binance']
                # Get exchange info for all symbols
                info = binance._request('GET', '/api/v3/exchangeInfo', {}) if hasattr(binance, '_request') else None
                if info and 'symbols' in info:
                    for s in info['symbols']:
                        if s.get('status') == 'TRADING':
                            sym = s.get('symbol', '')
                            universe.append((sym, 'binance'))
                else:
                    # Fallback: get from tickers
                    tickers = binance.get_24h_tickers() if hasattr(binance, 'get_24h_tickers') else []
                    for t in tickers:
                        sym = t.get('symbol', '')
                        if sym:
                            universe.append((sym, 'binance'))
                logger.info(f"🔍 Binance: discovered {len([u for u in universe if u[1]=='binance'])} symbols")
            except Exception as e:
                logger.warning(f"Binance discovery failed: {e}")
        
        logger.info(f"🌐 Total universe: {len(universe)} symbols across {len(clients)} exchanges")
        return universe
    
    def fetch_historical_ohlcv(self, symbol: str, exchange: str, days: int = SEED_DAYS) -> List[Dict]:
        """
        Fetch historical OHLCV data for a symbol.
        Returns list of candles: [{timestamp, open, high, low, close, volume}, ...]
        """
        clients = self._get_clients()
        candles = []
        
        try:
            if exchange == 'kraken' and 'kraken' in clients:
                kraken = clients['kraken']
                # Kraken OHLC endpoint: interval in minutes
                # 60 = 1 hour
                since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
                
                # Use public OHLC endpoint
                resp = kraken.session.get(
                    f"{kraken.base}/0/public/OHLC",
                    params={'pair': symbol, 'interval': 60, 'since': since},
                    timeout=30
                )
                data = resp.json()
                
                if data.get('error'):
                    logger.debug(f"Kraken OHLC error for {symbol}: {data['error']}")
                    return []
                
                result = data.get('result', {})
                # Result has the pair data under a key (may differ from input symbol)
                for key, ohlc_data in result.items():
                    if key == 'last':
                        continue
                    for c in ohlc_data:
                        # Kraken format: [time, open, high, low, close, vwap, volume, count]
                        candles.append({
                            'timestamp': float(c[0]),
                            'open': float(c[1]),
                            'high': float(c[2]),
                            'low': float(c[3]),
                            'close': float(c[4]),
                            'volume': float(c[6])
                        })
                    break  # Only take first (the actual pair data)
                    
            elif exchange == 'binance' and 'binance' in clients:
                binance = clients['binance']
                # Binance klines endpoint
                end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
                start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
                
                resp = binance.session.get(
                    f"{binance.base}/api/v3/klines",
                    params={
                        'symbol': symbol,
                        'interval': '1h',
                        'startTime': start_time,
                        'endTime': end_time,
                        'limit': 1000
                    },
                    timeout=30
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    for c in data:
                        # Binance format: [open_time, open, high, low, close, volume, close_time, ...]
                        candles.append({
                            'timestamp': float(c[0]) / 1000,  # Convert ms to seconds
                            'open': float(c[1]),
                            'high': float(c[2]),
                            'low': float(c[3]),
                            'close': float(c[4]),
                            'volume': float(c[5])
                        })
                else:
                    logger.debug(f"Binance klines error for {symbol}: {resp.status_code}")
                    
        except Exception as e:
            logger.debug(f"Failed to fetch OHLCV for {symbol}@{exchange}: {e}")
            
        return candles
    
    def _hilbert_transform(self, prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute instantaneous phase and amplitude using Hilbert transform.
        Returns (phase_array, amplitude_array)
        """
        if len(prices) < 10:
            return np.zeros(len(prices)), np.ones(len(prices))
        
        # Detrend the signal
        detrended = prices - np.mean(prices)
        
        # Simple discrete Hilbert transform approximation
        # Using FFT-based approach
        n = len(detrended)
        fft = np.fft.fft(detrended)
        
        # Create Hilbert filter
        h = np.zeros(n)
        if n > 0:
            h[0] = 1
            if n % 2 == 0:
                h[1:n//2] = 2
                h[n//2] = 1
            else:
                h[1:(n+1)//2] = 2
        
        analytic = np.fft.ifft(fft * h)
        
        amplitude = np.abs(analytic)
        phase = np.angle(analytic)
        
        # Normalize amplitude
        if np.max(amplitude) > 0:
            amplitude = amplitude / np.max(amplitude)
        
        return phase, amplitude
    
    def _dominant_frequency(self, prices: np.ndarray, sample_rate: float = 1.0) -> float:
        """
        Find dominant frequency in the price series using FFT.
        sample_rate = samples per hour (1.0 for hourly candles)
        """
        if len(prices) < 10:
            return SCHUMANN_BASE
        
        # Detrend
        detrended = prices - np.mean(prices)
        
        # FFT
        fft = np.fft.fft(detrended)
        freqs = np.fft.fftfreq(len(detrended), d=1.0/sample_rate)
        
        # Get magnitude spectrum (positive frequencies only)
        pos_mask = freqs > 0
        magnitudes = np.abs(fft[pos_mask])
        pos_freqs = freqs[pos_mask]
        
        if len(magnitudes) == 0:
            return SCHUMANN_BASE
        
        # Find dominant frequency
        dominant_idx = np.argmax(magnitudes)
        dominant_freq = pos_freqs[dominant_idx]
        
        # Convert to cycles per day (more intuitive for markets)
        # 1 sample = 1 hour, so freq in cycles/hour
        # Multiply by 24 for cycles/day
        dominant_freq_daily = dominant_freq * 24
        
        return max(0.1, dominant_freq_daily)  # Minimum 0.1 cycles/day
    
    def _calculate_coherence(self, series1: np.ndarray, series2: np.ndarray) -> float:
        """Calculate coherence between two price series"""
        if len(series1) < 10 or len(series2) < 10:
            return 0.0
        
        # Normalize both series
        s1 = (series1 - np.mean(series1)) / (np.std(series1) + 1e-8)
        s2 = (series2 - np.mean(series2)) / (np.std(series2) + 1e-8)
        
        # Truncate to same length
        min_len = min(len(s1), len(s2))
        s1, s2 = s1[:min_len], s2[:min_len]
        
        # Correlation as coherence proxy
        coherence = np.corrcoef(s1, s2)[0, 1]
        
        # Handle NaN
        if np.isnan(coherence):
            return 0.0
        
        return float(coherence)
    
    def build_wave_state(self, symbol: str, candles: List[Dict]) -> Optional[SymbolWaveState]:
        """Build wave state from OHLCV candles"""
        if len(candles) < 10:
            return None
        
        # Extract price and volume series
        prices = np.array([c['close'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        # Calculate wave properties
        phase_array, amplitude_array = self._hilbert_transform(prices)
        dominant_freq = self._dominant_frequency(prices)
        
        # Current values (latest)
        current_phase = float(phase_array[-1])
        current_amplitude = float(np.std(prices) / (np.mean(prices) + 1e-8))  # Normalized volatility
        
        # Velocity (rate of price change)
        velocity = float((prices[-1] - prices[-2]) / (prices[-2] + 1e-8)) if len(prices) > 1 else 0.0
        
        # Self-coherence (consistency of the wave pattern)
        if len(prices) > 20:
            half = len(prices) // 2
            self_coherence = self._calculate_coherence(prices[:half], prices[half:])
        else:
            self_coherence = 0.5
        
        return SymbolWaveState(
            symbol=symbol,
            phase=current_phase,
            amplitude=current_amplitude,
            frequency=dominant_freq,
            velocity=velocity,
            coherence=self_coherence,
            last_price=float(prices[-1]),
            last_volume=float(volumes[-1]),
            last_update=time.time(),
            price_history=prices.tolist()[-SEED_CANDLE_COUNT:],  # Keep last 7 days
            volume_history=volumes.tolist()[-SEED_CANDLE_COUNT:],
            phase_history=phase_array.tolist()[-SEED_CANDLE_COUNT:]
        )
    
    def build_coherence_matrix(self, states: Dict[str, SymbolWaveState], top_n: int = 50) -> Dict[str, Dict[str, float]]:
        """
        Build cross-symbol coherence matrix.
        Limited to top_n symbols by volume to keep computation manageable.
        """
        # Sort by volume and take top N
        sorted_symbols = sorted(
            states.items(),
            key=lambda x: x[1].last_volume,
            reverse=True
        )[:top_n]
        
        matrix = {}
        symbols = [s[0] for s in sorted_symbols]
        
        for i, sym1 in enumerate(symbols):
            matrix[sym1] = {}
            state1 = states[sym1]
            prices1 = np.array(state1.price_history)
            
            for sym2 in symbols[i+1:]:  # Upper triangle only
                state2 = states[sym2]
                prices2 = np.array(state2.price_history)
                
                coherence = self._calculate_coherence(prices1, prices2)
                matrix[sym1][sym2] = coherence
        
        return matrix
    
    def calculate_global_metrics(self, states: Dict[str, SymbolWaveState], coherence_matrix: Dict) -> Tuple[float, float, float, str]:
        """
        Calculate global harmonic metrics:
        - global_phase: average phase across all symbols
        - global_coherence: average coherence
        - dominant_frequency: market-wide dominant frequency
        - market_regime: bullish/bearish/neutral
        """
        if not states:
            return 0.0, 0.0, SCHUMANN_BASE, "neutral"
        
        # Global phase (weighted by volume)
        total_volume = sum(s.last_volume for s in states.values()) + 1e-8
        global_phase = sum(s.phase * s.last_volume for s in states.values()) / total_volume
        
        # Global coherence (average of matrix)
        coherence_values = []
        for sym1, inner in coherence_matrix.items():
            for sym2, coh in inner.items():
                coherence_values.append(abs(coh))
        global_coherence = np.mean(coherence_values) if coherence_values else 0.5
        
        # Dominant frequency (volume-weighted average)
        dominant_freq = sum(s.frequency * s.last_volume for s in states.values()) / total_volume
        
        # Market regime from aggregate velocity
        avg_velocity = np.mean([s.velocity for s in states.values()])
        if avg_velocity > 0.01:
            regime = "bullish"
        elif avg_velocity < -0.01:
            regime = "bearish"
        else:
            regime = "neutral"
        
        return float(global_phase), float(global_coherence), float(dominant_freq), regime
    
    def load_seed(self, max_symbols: int = 200, force_refresh: bool = False) -> GlobalHarmonicState:
        """
        Load the harmonic seed, either from cache or by fetching fresh data.
        
        Args:
            max_symbols: Maximum number of symbols to include (by volume)
            force_refresh: If True, ignore cache and fetch fresh
        
        Returns:
            GlobalHarmonicState ready for live growth
        """
        cache_file = self.cache_dir / "harmonic_seed.json"
        legacy_pickle = self.cache_dir / "harmonic_seed.pkl"
        cache_meta = self.cache_dir / "harmonic_seed_meta.json"

        if legacy_pickle.exists():
            logger.warning(
                "Legacy harmonic_seed.pkl ignored: pickle deserialization is disabled"
            )
        
        # Check cache
        if not force_refresh and cache_file.exists() and cache_meta.exists():
            try:
                with open(cache_meta, 'r') as f:
                    meta = json.load(f)
                
                # Cache valid for 6 hours
                cache_age = time.time() - meta.get('timestamp', 0)
                if cache_age < 6 * 3600:
                    logger.info(f"📦 Loading cached harmonic seed (age: {cache_age/3600:.1f}h)")
                    if cache_file.stat().st_size > MAX_HARMONIC_CACHE_BYTES:
                        raise ValueError("harmonic_seed_cache_too_large")
                    decoded = _decode_harmonic_cache(cache_file.read_bytes())
                    self.state = GlobalHarmonicState.from_dict(decoded)
                    return self.state
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")
        
        logger.info("🌱 Building fresh harmonic seed from 7-day history...")
        
        # 1. Discover universe
        universe = self.discover_universe()
        
        # 2. Fetch historical data for each symbol
        symbol_candles = {}
        fetched = 0
        
        for symbol, exchange in universe:
            if fetched >= max_symbols * 2:  # Fetch extra, will filter by volume later
                break
            
            candles = self.fetch_historical_ohlcv(symbol, exchange)
            if candles and len(candles) >= 20:
                key = f"{symbol}@{exchange}"
                symbol_candles[key] = candles
                fetched += 1
                
                if fetched % 50 == 0:
                    logger.info(f"  📊 Fetched {fetched} symbols...")
            
            # Rate limiting
            time.sleep(0.1)
        
        logger.info(f"📊 Fetched historical data for {len(symbol_candles)} symbols")
        
        # 3. Build wave states
        for key, candles in symbol_candles.items():
            state = self.build_wave_state(key, candles)
            if state:
                self.state.symbols[key] = state
        
        logger.info(f"🌊 Built wave states for {len(self.state.symbols)} symbols")
        
        # 4. Filter to top N by volume
        if len(self.state.symbols) > max_symbols:
            sorted_states = sorted(
                self.state.symbols.items(),
                key=lambda x: x[1].last_volume,
                reverse=True
            )[:max_symbols]
            self.state.symbols = dict(sorted_states)
            logger.info(f"📉 Filtered to top {max_symbols} by volume")
        
        # 5. Build coherence matrix
        self.state.coherence_matrix = self.build_coherence_matrix(self.state.symbols)
        logger.info("🔗 Built coherence matrix")
        
        # 6. Calculate global metrics
        (self.state.global_phase,
         self.state.global_coherence,
         self.state.dominant_frequency,
         self.state.market_regime) = self.calculate_global_metrics(
            self.state.symbols,
            self.state.coherence_matrix
        )
        
        # Schumann alignment (how close dominant freq is to Schumann harmonics)
        schumann_harmonics = [SCHUMANN_BASE * n for n in range(1, 10)]
        min_dist = min(abs(self.state.dominant_frequency - h) for h in schumann_harmonics)
        self.state.schumann_alignment = 1.0 / (1.0 + min_dist)
        
        self.state.last_update = time.time()
        self.state.candle_count = SEED_CANDLE_COUNT
        
        # 7. Cache the result
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(
                    self.state.to_dict(),
                    f,
                    ensure_ascii=True,
                    allow_nan=False,
                    separators=(',', ':'),
                    sort_keys=True,
                )
            with open(cache_meta, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': time.time(),
                    'symbols': len(self.state.symbols),
                    'candles': SEED_CANDLE_COUNT
                }, f)
            logger.info("💾 Cached harmonic seed")
        except Exception as e:
            logger.warning(f"Failed to cache seed: {e}")
        
        logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║  🌊 HARMONIC SEED LOADED                                     ║
╠══════════════════════════════════════════════════════════════╣
║  Symbols:           {len(self.state.symbols):>6}                               ║
║  Candles/Symbol:    {SEED_CANDLE_COUNT:>6} (7 days)                        ║
║  Global Phase:      {self.state.global_phase:>6.3f} rad                          ║
║  Global Coherence:  {self.state.global_coherence:>6.3f}                               ║
║  Dominant Freq:     {self.state.dominant_frequency:>6.2f} cycles/day                  ║
║  Schumann Align:    {self.state.schumann_alignment:>6.3f}                               ║
║  Market Regime:     {self.state.market_regime:>10}                         ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        return self.state
    
    def get_state(self) -> GlobalHarmonicState:
        """Get current state (load if needed)"""
        if not self.state.symbols:
            return self.load_seed()
        return self.state


# ═══════════════════════════════════════════════════════════════
# LIVE GROWTH ENGINE
# ═══════════════════════════════════════════════════════════════

class HarmonicGrowthEngine:
    """
    Incrementally grows the harmonic wave model with live tick data.
    Like a 3D printer adding layers to the existing form.
    """
    
    def __init__(self, seed_state: GlobalHarmonicState):
        self.state = seed_state
        self.tick_buffer: Dict[str, List[Tuple[float, float, float]]] = {}  # symbol -> [(ts, price, vol), ...]
        self.last_candle_time: Dict[str, float] = {}
        
    def ingest_tick(self, symbol: str, price: float, volume: float, timestamp: float = None):
        """
        Ingest a live price tick. Ticks are buffered and aggregated into candles.
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Buffer the tick
        if symbol not in self.tick_buffer:
            self.tick_buffer[symbol] = []
        self.tick_buffer[symbol].append((timestamp, price, volume))
        
        # Check if we should form a new candle (hourly)
        hour_start = (timestamp // 3600) * 3600
        last_candle = self.last_candle_time.get(symbol, 0)
        
        if hour_start > last_candle:
            self._form_candle(symbol, hour_start)
    
    def _form_candle(self, symbol: str, candle_time: float):
        """Form a candle from buffered ticks and update wave state"""
        buffer = self.tick_buffer.get(symbol, [])
        if not buffer:
            return
        
        # Find ticks for the previous hour
        prev_hour_start = candle_time - 3600
        hour_ticks = [(t, p, v) for t, p, v in buffer if prev_hour_start <= t < candle_time]
        
        if not hour_ticks:
            return
        
        # Form OHLCV
        prices = [p for _, p, _ in hour_ticks]
        volumes = [v for _, _, v in hour_ticks]
        
        candle = {
            'timestamp': candle_time,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': sum(volumes)
        }
        
        # Update wave state
        self._update_wave_state(symbol, candle)
        
        # Clear old ticks
        self.tick_buffer[symbol] = [(t, p, v) for t, p, v in buffer if t >= candle_time]
        self.last_candle_time[symbol] = candle_time
    
    def _update_wave_state(self, symbol: str, candle: Dict):
        """Incrementally update a symbol's wave state with new candle"""
        if symbol not in self.state.symbols:
            # New symbol - create minimal state
            self.state.symbols[symbol] = SymbolWaveState(
                symbol=symbol,
                last_price=candle['close'],
                last_volume=candle['volume'],
                last_update=time.time(),
                price_history=[candle['close']],
                volume_history=[candle['volume']],
                phase_history=[0.0]
            )
            return
        
        state = self.state.symbols[symbol]
        
        # Append new data (rolling window)
        state.price_history.append(candle['close'])
        state.volume_history.append(candle['volume'])
        
        # Keep window size
        max_history = SEED_CANDLE_COUNT + 24  # Allow some growth
        if len(state.price_history) > max_history:
            state.price_history = state.price_history[-SEED_CANDLE_COUNT:]
            state.volume_history = state.volume_history[-SEED_CANDLE_COUNT:]
            state.phase_history = state.phase_history[-SEED_CANDLE_COUNT:]
        
        # Incremental phase update (simplified - full recalc every N candles)
        prices = np.array(state.price_history)
        
        # Update velocity
        if len(prices) > 1:
            state.velocity = float((prices[-1] - prices[-2]) / (prices[-2] + 1e-8))
        
        # Update amplitude (recent volatility)
        if len(prices) > 10:
            recent = prices[-24:]  # Last 24 candles
            state.amplitude = float(np.std(recent) / (np.mean(recent) + 1e-8))
        
        # Recalculate phase periodically (every 6 candles)
        if len(prices) % 6 == 0 and len(prices) > 20:
            from scipy.signal import hilbert as scipy_hilbert
            try:
                detrended = prices - np.mean(prices)
                analytic = scipy_hilbert(detrended)
                phase = np.angle(analytic[-1])
                state.phase = float(phase)
                state.phase_history.append(state.phase)
            except ImportError:
                # Fallback without scipy
                state.phase = (state.phase + 0.1) % (2 * math.pi)
                state.phase_history.append(state.phase)
        
        state.last_price = candle['close']
        state.last_volume = candle['volume']
        state.last_update = time.time()
        
        # Update global state periodically
        self.state.candle_count += 1
        if self.state.candle_count % 10 == 0:
            self._update_global_metrics()
    
    def _update_global_metrics(self):
        """Update global harmonic metrics"""
        states = self.state.symbols
        if not states:
            return
        
        # Global phase (volume-weighted)
        total_volume = sum(s.last_volume for s in states.values()) + 1e-8
        self.state.global_phase = sum(s.phase * s.last_volume for s in states.values()) / total_volume
        
        # Aggregate velocity -> regime
        avg_velocity = np.mean([s.velocity for s in states.values()])
        if avg_velocity > 0.01:
            self.state.market_regime = "bullish"
        elif avg_velocity < -0.01:
            self.state.market_regime = "bearish"
        else:
            self.state.market_regime = "neutral"
        
        self.state.last_update = time.time()
    
    def get_state(self) -> GlobalHarmonicState:
        """Get current evolved state"""
        return self.state
    
    def get_symbol_state(self, symbol: str) -> Optional[SymbolWaveState]:
        """Get wave state for a specific symbol"""
        return self.state.symbols.get(symbol)


# ═══════════════════════════════════════════════════════════════
# CLI / TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("""
    🌊 HARMONIC WAVE SEED LOADER
    ════════════════════════════
    Building 7-day wave seed...
    """)
    
    loader = HarmonicSeedLoader()
    state = loader.load_seed(max_symbols=100)
    
    print(f"\n✅ Seed loaded with {len(state.symbols)} symbols")
    print(f"   Global coherence: {state.global_coherence:.3f}")
    print(f"   Market regime: {state.market_regime}")
    
    # Show top coherent pairs
    print("\n🔗 Top Coherent Pairs:")
    pairs = []
    for sym1, inner in state.coherence_matrix.items():
        for sym2, coh in inner.items():
            pairs.append((sym1, sym2, abs(coh)))
    
    for sym1, sym2, coh in sorted(pairs, key=lambda x: -x[2])[:10]:
        print(f"   {sym1[:20]:20} ↔ {sym2[:20]:20} : {coh:.3f}")
