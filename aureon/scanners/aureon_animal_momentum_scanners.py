"""
Alpaca animal-themed momentum scanners

Provides:
- AlpacaLoneWolf: momentum sniper (fast single-target decisions)
- AlpacaLionHunt: multi-target hunter (prioritize high momentum × volume prey)
- AlpacaArmyAnts: small-profit foraging (many small trades)
- AlpacaHummingbird: micro-rotation pollinator (ETH-quoted rotations)
- AlpacaSwarmOrchestrator: coordinates the above agents using AlpacaScannerBridge

This is a *smoke-first* implementation focusing on readability and safe dry-run behavior.

🚀 V2 OPTIMIZATION: Uses BATCH API calls + caching to minimize rate limiting!
- Single batch call for ALL symbols instead of per-symbol calls
- Cache results for 60 seconds
- Falls back to Binance/Kraken caches when available
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import json
import logging
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from aureon.exchanges.alpaca_client import AlpacaClient
from aureon.exchanges.alpaca_fee_tracker import AlpacaFeeTracker
from aureon.bridges.aureon_alpaca_scanner_bridge import AlpacaScannerBridge

logger = logging.getLogger(__name__)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# ════════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - Listen to Orca whale hunting signals!
# ════════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import ChirpDirection, ChirpType, get_chirp_bus
    CHIRP_BUS_AVAILABLE = True
    logger.info("🐦 Chirp Bus CONNECTED - Momentum scanners can hear Orca whale signals!")
except ImportError:
    logger.debug("🐦 Chirp Bus not available - momentum scanners won't receive Orca signals")
    CHIRP_BUS_AVAILABLE = False

# 📡 THOUGHT BUS INTEGRATION - Neural Persistence
THOUGHT_BUS_AVAILABLE = False
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# ════════════════════════════════════════════════════════════════════════════════
# 🌐 GLOBAL MARKET INTEGRATION - Full Exchange Coverage (same as Orca)
# ════════════════════════════════════════════════════════════════════════════════
# Kraken (crypto)
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

# Binance streaming (crypto real-time)
try:
    from aureon.exchanges.binance_ws_client import BinanceWebSocketClient
    BINANCE_WS_AVAILABLE = True
except ImportError:
    BINANCE_WS_AVAILABLE = False
    BinanceWebSocketClient = None

# Capital.com (CFDs + stocks)
try:
    from aureon.exchanges.capital_client import CapitalClient
    CAPITAL_AVAILABLE = True
except ImportError:
    CAPITAL_AVAILABLE = False
    CapitalClient = None

# Market scanners (global intelligence)
try:
    from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner
    WAVE_SCANNER_AVAILABLE = True
except ImportError:
    WAVE_SCANNER_AVAILABLE = False
    GlobalWaveScanner = None

# ════════════════════════════════════════════════════════════════════════════════
# 🎯 GLOBAL BATCH CACHE - One API call serves ALL animal scanners!
# ════════════════════════════════════════════════════════════════════════════════
_BATCH_BARS_CACHE: Dict[str, Any] = {}
_BATCH_CACHE_TIME: float = 0
_BATCH_CACHE_TTL: float = 60.0  # 60 second cache (was per-symbol calls!)


@dataclass
class AnimalOpportunity:
    symbol: str
    side: str  # 'buy' or 'sell'
    move_pct: float
    net_pct: float
    volume: float
    reason: str = ""
    truth_status: str = "no_data"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    generated_values: bool = False
    eligible_for_external_action: bool = False


MAX_LATEST_BAR_AGE_SECONDS = 2 * 60 * 60
MAX_HISTORICAL_BAR_AGE_SECONDS = 48 * 60 * 60
MAX_SOURCE_CLOCK_SKEW_SECONDS = 5 * 60


def _finite_float(value: Any, *, positive: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    return number


def _required_number(
    payload: Dict[str, Any],
    *keys: str,
    positive: bool = False,
) -> Optional[float]:
    for key in keys:
        if key in payload and payload[key] is not None:
            return _finite_float(payload[key], positive=positive)
    return None


def _source_timestamp(payload: Dict[str, Any]) -> Optional[float]:
    raw = None
    for key in ("source_timestamp", "t", "timestamp", "event_time", "E", "close_time", "C"):
        if key in payload and payload[key] is not None:
            raw = payload[key]
            break
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value > 10_000_000_000:
            value /= 1000.0
        return value if math.isfinite(value) and value > 0 else None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError):
        return None


def _normalise_provider_bars(
    bars: Any,
    *,
    source_id: str,
    received_at: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return only complete, timestamped provider bars.

    Receipt time is kept separate and is never substituted for source time.
    """
    received = time.time() if received_at is None else float(received_at)
    if not isinstance(bars, list) or not bars:
        return []
    normalised: List[Dict[str, Any]] = []
    for bar in bars:
        if not isinstance(bar, dict):
            return []
        opened = _required_number(bar, "o", "open", positive=True)
        closed = _required_number(bar, "c", "close", positive=True)
        high = _required_number(bar, "h", "high", positive=True)
        low = _required_number(bar, "l", "low", positive=True)
        volume = _required_number(bar, "v", "volume")
        observed_at = _source_timestamp(bar)
        if None in (opened, closed, high, low, volume, observed_at):
            return []
        assert opened is not None and closed is not None
        assert high is not None and low is not None and volume is not None
        assert observed_at is not None
        age = received - observed_at
        if (
            volume < 0
            or high < max(opened, closed)
            or low > min(opened, closed)
            or age < -MAX_SOURCE_CLOCK_SKEW_SECONDS
            or age > MAX_HISTORICAL_BAR_AGE_SECONDS
        ):
            return []
        normalised.append(
            {
                "o": opened,
                "c": closed,
                "h": high,
                "l": low,
                "v": volume,
                "source_id": str(bar.get("source_id") or source_id),
                "source_timestamp": observed_at,
                "received_at": received,
                "truth_status": "live",
                "generated_values": False,
            }
        )
    normalised.sort(key=lambda item: item["source_timestamp"])
    if received - normalised[-1]["source_timestamp"] > MAX_LATEST_BAR_AGE_SECONDS:
        return []
    return normalised


def _bar_series_provenance(bars: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not bars:
        return None
    latest = bars[-1]
    source_id = latest.get("source_id")
    source_ts = _finite_float(latest.get("source_timestamp"), positive=True)
    received_at = _finite_float(latest.get("received_at"), positive=True)
    if (
        latest.get("truth_status") not in {"live", "real_derived"}
        or not source_id
        or source_ts is None
        or received_at is None
        or latest.get("generated_values") is not False
        or received_at - source_ts > MAX_LATEST_BAR_AGE_SECONDS
    ):
        return None
    return {
        "truth_status": "real_derived",
        "source_id": str(source_id),
        "source_timestamp": source_ts,
        "received_at": received_at,
        "generated_values": False,
        "eligible_for_external_action": True,
    }


def _bar_series_metrics(
    bars: List[Dict[str, Any]],
) -> Optional[Tuple[float, float, float, Dict[str, Any]]]:
    provenance = _bar_series_provenance(bars)
    if provenance is None:
        return None
    first_price = _required_number(bars[0], "o", "open", positive=True)
    last_price = _required_number(bars[-1], "c", "close", positive=True)
    volumes = [_required_number(bar, "v", "volume") for bar in bars]
    if (
        first_price is None
        or last_price is None
        or any(volume is None or volume < 0 for volume in volumes)
    ):
        return None
    return first_price, last_price, sum(volume for volume in volumes if volume is not None), provenance


def _read_external_cache(cache_file: str, max_age: float = 300) -> Optional[Dict]:
    """Read Binance/Kraken/CoinGecko WS cache if available (FREE data source!)"""
    try:
        # Try multiple paths
        paths_to_try = [
            Path(cache_file),
            Path("ws_cache") / Path(cache_file).name,
            Path("ws_cache/ws_prices.json"),  # CoinGecko feeder output
            Path("coingecko_market_cache.json"),
        ]
        
        for p in paths_to_try:
            if not p.exists():
                continue
            raw = p.read_text(encoding='utf-8')
            data = json.loads(raw) if raw else {}
            generated_at = data.get('generated_at')
            if generated_at is None:
                continue
            ts = float(generated_at)
            if math.isfinite(ts) and ts > 0 and 0 <= (time.time() - ts) <= max_age:
                logger.debug(f"🎯 Found fresh cache: {p}")
                return data
    except Exception as e:
        logger.debug(f"Cache read error: {e}")
    return None


class BaseAnimalScanner:
    def __init__(self, alpaca: AlpacaClient, bridge: AlpacaScannerBridge):
        self.alpaca = alpaca
        self.bridge = bridge
        self._bars_cache: Dict[str, List[Dict]] = {}
        self._cache_time: float = 0
        
        # 🌐 GLOBAL MARKET CLIENTS - Direct access to all exchanges
        self.kraken_client: Optional[Any] = None
        self.binance_ws: Optional[Any] = None
        self.capital_client: Optional[Any] = None
        self.wave_scanner: Optional[Any] = None
        
        # 🐦 ORCA WHALE TARGETS - Listen to whale hunting signals via chirp bus
        self._orca_whale_targets: List[str] = []  # Symbols Orca detected whales on
        self._orca_target_time: float = 0
        
        # Initialize global market connections
        self._init_market_connections()
        
        # Subscribe to Orca whale signals if chirp bus available
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                # Subscribe to WHALE_DETECTED signals from Orca
                chirp_bus.subscribe('WHALE_DETECTED', self._on_whale_detected)
                logger.info("🦈 Momentum scanner SUBSCRIBED to Orca whale signals!")
            except Exception as e:
                logger.debug(f"Could not subscribe to chirp bus: {e}")
    
    def _on_whale_detected(self, signal_data: Dict):
        """Called when Orca detects a whale movement - prioritize this symbol!"""
        try:
            symbol = signal_data.get('symbol')
            coherence = _finite_float(signal_data.get('coherence'))
            source_timestamp = _source_timestamp(signal_data)
            now = time.time()
            signal_is_proven = (
                signal_data.get('truth_status') in {'live', 'real_derived'}
                and bool(signal_data.get('source_id'))
                and source_timestamp is not None
                and 0 <= now - source_timestamp <= 5 * 60
                and signal_data.get('generated_values') is False
            )
            if symbol and coherence is not None and coherence > 0.5 and signal_is_proven:
                # Add to priority target list (dedupe)
                if symbol not in self._orca_whale_targets:
                    self._orca_whale_targets.append(symbol)
                    self._orca_target_time = now
                    logger.info(f"🦈→🎯 Orca detected whale on {symbol} - PRIORITY TARGET!")
                # Keep list manageable (max 20 recent whale signals)
                if len(self._orca_whale_targets) > 20:
                    self._orca_whale_targets = self._orca_whale_targets[-20:]
        except Exception as e:
            logger.debug(f"Error processing whale signal: {e}")
    
    def _init_market_connections(self):
        """Initialize connections to all global market feeds - same as Orca."""
        market_count = 0
        
        # Kraken (crypto spot)
        if KRAKEN_AVAILABLE:
            try:
                self.kraken_client = get_kraken_client()
                market_count += 1
                logger.info("🐙 Momentum scanner → Kraken CONNECTED")
            except Exception as e:
                logger.debug(f"Kraken connection failed: {e}")
        
        # Binance WebSocket (real-time crypto streaming)
        if BINANCE_WS_AVAILABLE:
            try:
                self.binance_ws = BinanceWebSocketClient()
                if os.getenv('BINANCE_API_KEY'):
                    market_count += 1
                    logger.info("🟡 Momentum scanner → Binance WS READY")
                else:
                    logger.debug("Binance API key not set")
            except Exception as e:
                logger.debug(f"Binance WS connection failed: {e}")
        
        # Capital.com (CFDs + global stocks)
        if CAPITAL_AVAILABLE:
            try:
                self.capital_client = CapitalClient()
                if self.capital_client.is_authenticated():
                    market_count += 1
                    logger.info("💼 Momentum scanner → Capital.com CONNECTED")
                else:
                    self.capital_client = None
            except Exception as e:
                logger.debug(f"Capital.com connection failed: {e}")
        
        # Global Wave Scanner
        if WAVE_SCANNER_AVAILABLE:
            try:
                self.wave_scanner = GlobalWaveScanner()
                market_count += 1
                logger.info("🌊 Momentum scanner → Wave Scanner CONNECTED")
            except Exception as e:
                logger.debug(f"Wave scanner init failed: {e}")
        
        if market_count > 0:
            logger.info(f"🌐 Momentum scanner has {market_count} additional market feeds")
    
    def scan_global_markets(self, symbols: Optional[List[str]] = None) -> List[AnimalOpportunity]:
        """Scan all connected markets for momentum opportunities - same proactive hunting as Orca."""
        opportunities = []
        
        if symbols is None:
            symbols = self._get_crypto_universe()[:20]  # Top 20 for efficiency
        
        scan_start = time.time()
        
        # Scan Kraken for momentum
        if self.kraken_client:
            try:
                for symbol in symbols:
                    ticker = self.kraken_client.get_ticker(symbol)
                    if not isinstance(ticker, dict):
                        continue
                    closes = ticker.get("c")
                    opens = ticker.get("o")
                    volumes = ticker.get("v")
                    observed_at = _source_timestamp(ticker)
                    if (
                        not isinstance(closes, (list, tuple))
                        or not closes
                        or not isinstance(opens, (list, tuple))
                        or not opens
                        or not isinstance(volumes, (list, tuple))
                        or len(volumes) < 2
                        or observed_at is None
                    ):
                        continue
                    price = _finite_float(closes[0], positive=True)
                    open_price = _finite_float(opens[0], positive=True)
                    base_volume = _finite_float(volumes[1])
                    received_at = time.time()
                    if (
                        price is None
                        or open_price is None
                        or base_volume is None
                        or base_volume < 0
                        or received_at - observed_at > MAX_LATEST_BAR_AGE_SECONDS
                    ):
                        continue
                    move_pct = ((price - open_price) / open_price) * 100
                    if abs(move_pct) > 0.5:
                        is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                        if not is_profitable:
                            continue
                        opportunities.append(
                            AnimalOpportunity(
                                symbol=symbol,
                                side='buy' if move_pct > 0 else 'sell',
                                move_pct=abs(move_pct),
                                net_pct=self.bridge.calculate_net_profit(abs(move_pct)),
                                volume=base_volume * price,
                                reason=f"Kraken momentum ({tier}): {move_pct:+.2f}%",
                                truth_status="real_derived",
                                source_id="kraken_rest_ticker",
                                source_timestamp=observed_at,
                                received_at=received_at,
                                generated_values=False,
                                eligible_for_external_action=True,
                            )
                        )
            except Exception as e:
                logger.debug(f"Kraken scan error: {e}")
        
        # Scan Binance WebSocket for momentum
        if self.binance_ws and hasattr(self.binance_ws, 'get_latest_ticker'):
            try:
                for symbol in symbols:
                    ticker = self.binance_ws.get_latest_ticker(symbol)
                    if not isinstance(ticker, dict):
                        continue
                    move_pct = _required_number(ticker, "priceChangePercent")
                    volume = _required_number(ticker, "quoteVolume")
                    observed_at = _source_timestamp(ticker)
                    received_at = time.time()
                    if (
                        move_pct is None
                        or volume is None
                        or volume < 0
                        or observed_at is None
                        or received_at - observed_at > MAX_LATEST_BAR_AGE_SECONDS
                        or abs(move_pct) <= 0.5
                    ):
                        continue
                    is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                    if not is_profitable:
                        continue
                    opportunities.append(
                        AnimalOpportunity(
                            symbol=symbol,
                            side='buy' if move_pct > 0 else 'sell',
                            move_pct=abs(move_pct),
                            net_pct=self.bridge.calculate_net_profit(abs(move_pct)),
                            volume=volume,
                            reason=f"Binance momentum ({tier}): {move_pct:+.2f}%",
                            truth_status="real_derived",
                            source_id="binance_websocket_ticker",
                            source_timestamp=observed_at,
                            received_at=received_at,
                            generated_values=False,
                            eligible_for_external_action=True,
                        )
                    )
            except Exception as e:
                logger.debug(f"Binance scan error: {e}")
        
        # Use Wave Scanner for aggregated opportunities
        if self.wave_scanner and hasattr(self.wave_scanner, 'get_hot_opportunities'):
            try:
                wave_opps = self.wave_scanner.get_hot_opportunities(min_score=0.6)
                for wo in wave_opps:
                    if not isinstance(wo, dict):
                        continue
                    source_timestamp = _finite_float(wo.get("source_timestamp"), positive=True)
                    received_at = _finite_float(wo.get("received_at"), positive=True)
                    source_id = wo.get("source_id")
                    move_pct = _finite_float(wo.get("move_pct"))
                    net_pct = _finite_float(wo.get("net_pct"))
                    volume = _finite_float(wo.get("volume_usd"))
                    if (
                        wo.get("truth_status") not in {"live", "real_derived"}
                        or not source_id
                        or source_timestamp is None
                        or received_at is None
                        or move_pct is None
                        or net_pct is None
                        or volume is None
                        or volume < 0
                        or received_at - source_timestamp > MAX_LATEST_BAR_AGE_SECONDS
                        or wo.get("generated_values") is not False
                    ):
                        continue
                    opp = AnimalOpportunity(
                        symbol=str(wo.get('symbol') or ''),
                        side='buy' if wo.get('direction') == 'up' else 'sell',
                        move_pct=move_pct,
                        net_pct=net_pct,
                        volume=volume,
                        reason=f"Wave scanner: {wo.get('reason') or 'provider-derived signal'}",
                        truth_status="real_derived",
                        source_id=str(source_id),
                        source_timestamp=source_timestamp,
                        received_at=received_at,
                        generated_values=False,
                        eligible_for_external_action=True,
                    )
                    if opp.symbol:
                        opportunities.append(opp)
            except Exception as e:
                logger.debug(f"Wave scanner error: {e}")
        
        scan_duration = time.time() - scan_start
        
        if opportunities:
            logger.info(f"🌊 Global scan: {len(opportunities)} opportunities from all markets ({scan_duration:.2f}s)")
        
        return opportunities
    
    def _get_crypto_universe(self) -> List[str]:
        # 🦈 PRIORITY: Put Orca whale targets at front of scan list!
        base_universe = []
        
        # Prefer bridge cached list if available; else query Alpaca
        if self.bridge and self.bridge._crypto_universe:
            base_universe = sorted(list(self.bridge._crypto_universe))
        else:
            assets = self.alpaca.list_assets(status='active', asset_class='crypto') or []
            syms = []
            for a in assets:
                sym = a.get('symbol') if isinstance(a, dict) else getattr(a, 'symbol', None)
                if sym:
                    if '/' not in sym:
                        sym = f"{sym}/USD"
                    syms.append(sym)
            base_universe = sorted(syms)
        
        # 🎯 FILTER: Only USD pairs - USDC/USDT/BTC pairs have no historical data for Nexus!
        base_universe = [s for s in base_universe if s.endswith('/USD') and 
                        'USDC' not in s and 'USDT' not in s]
        
        # 🦈 WHALE WAKE RIDING: Prioritize Orca-detected whale symbols first!
        # Clear stale targets after 5 minutes
        if time.time() - self._orca_target_time > 300:
            self._orca_whale_targets = []
        
        # Put whale targets at front of list
        whale_targets = [s for s in self._orca_whale_targets if s in base_universe]
        other_symbols = [s for s in base_universe if s not in whale_targets]
        
        if whale_targets:
            logger.info(f"🦈 WHALE WAKE RIDING: Scanning {len(whale_targets)} Orca targets first!")
        
        return whale_targets + other_symbols
    
    def _get_all_bars_batched(self, symbols: List[str], limit: int = 24) -> Dict[str, List[Dict]]:
        """
        🚀 BATCH API OPTIMIZATION: One call for ALL symbols!
        
        This replaces N individual calls with 1 batch call.
        If N=50 symbols, this reduces API calls from 50 to 1!
        """
        global _BATCH_BARS_CACHE, _BATCH_CACHE_TIME
        
        # Use global cache if fresh (serves ALL animal scanners!)
        if _BATCH_BARS_CACHE and (time.time() - _BATCH_CACHE_TIME) < _BATCH_CACHE_TTL:
            logger.debug(f"🎯 Using cached batch bars ({len(_BATCH_BARS_CACHE)} symbols)")
            return _BATCH_BARS_CACHE
        
        # Ticker-only caches are useful status surfaces, but they are not OHLC
        # receipts. The previous implementation invented high/low values at
        # +/-1% and treated the result as a provider bar. Only an explicit
        # provider bar series may enter momentum scoring.
        binance_cache = _read_external_cache('binance_ws_cache.json', max_age=120)
        if binance_cache:
            logger.debug("Binance ticker cache is not a timestamped OHLC source; requesting provider bars")

        kraken_cache = _read_external_cache('kraken_market_cache.json', max_age=120)
        if kraken_cache:
            logger.debug("Kraken ticker cache is not a timestamped OHLC source; requesting provider bars")
        
        # 🦙 ALPACA BATCH CALL (only if external caches unavailable)
        try:
            # Resolve all symbols first
            resolved_map = {}
            for sym in symbols:
                resolved = sym
                if hasattr(self.alpaca, '_resolve_symbol'):
                    resolved = self.alpaca._resolve_symbol(sym) or sym
                resolved_map[resolved] = sym
            
            resolved_list = list(resolved_map.keys())
            if not resolved_list:
                return {}
            
            # 🎯 SINGLE BATCH CALL for ALL symbols!
            logger.info(f"🦙 Batch fetching bars for {len(resolved_list)} symbols (1 API call)")
            bars_resp = self.alpaca.get_crypto_bars(resolved_list, timeframe='1H', limit=limit) or {}
            
            result = {}
            bars_data = bars_resp.get('bars', {}) if isinstance(bars_resp, dict) else {}
            
            for resolved_sym, bars in bars_data.items():
                orig_sym = resolved_map.get(resolved_sym, resolved_sym)
                normalised = _normalise_provider_bars(
                    bars,
                    source_id="alpaca_crypto_bars_1h",
                )
                if normalised:
                    result[orig_sym] = normalised
            
            # Update global cache
            _BATCH_BARS_CACHE = result
            _BATCH_CACHE_TIME = time.time()
            logger.info(f"🎯 Cached {len(result)} symbol bars for 60s")
            
            return result
            
        except Exception as e:
            logger.warning(f"Batch bars fetch failed: {e}")
            return {}


class AlpacaLoneWolf(BaseAnimalScanner):
    """Momentum sniper.

    - Scans universe for large, clean 24h moves
    - Prefers high net profit (after fees)
    - Returns top N immediate trade suggestions (dry-run safe)
    
    🚀 V2: Uses batch cached data - ZERO individual API calls!
    """

    def find_targets(self, limit: int = 10) -> List[AnimalOpportunity]:
        symbols = self._get_crypto_universe()
        results: List[AnimalOpportunity] = []
        
        # 🚀 BATCH: Get all bars in ONE call (or from cache)
        all_bars = self._get_all_bars_batched(symbols, limit=24)
        
        for sym in symbols:
            try:
                bars = all_bars.get(sym, [])
                if not bars or len(bars) < 1:
                    continue

                metrics = _bar_series_metrics(bars)
                if metrics is None:
                    continue
                first_price, last_price, vol, provenance = metrics

                move_pct = ((last_price - first_price) / first_price) * 100.0

                is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                net = self.bridge.calculate_net_profit(abs(move_pct))

                if not is_profitable:
                    continue

                side = 'buy' if move_pct < 0 else 'sell'
                reason = f"Wolf ({tier})"
                results.append(
                    AnimalOpportunity(
                        symbol=sym,
                        side=side,
                        move_pct=move_pct,
                        net_pct=net,
                        volume=vol,
                        reason=reason,
                        **provenance,
                    )
                )

            except Exception:
                continue

        # Sort by net profit then by volume
        results.sort(key=lambda x: (-(x.net_pct), -x.volume))
        return results[:limit]


class AlpacaLionHunt(BaseAnimalScanner):
    """Hunts a pride (subset) and chooses the best prey using composite score.

    Score = |24h move| * log(1 + volume) * coherence_weight
    
    🚀 V2: Uses batch cached data - ZERO individual API calls!
    """

    def score_symbol(self, sym: str, bars: List[Dict]) -> Optional[Tuple[float, AnimalOpportunity]]:
        """Score a symbol using pre-fetched bars (no API call!)"""
        try:
            if not bars or len(bars) < 1:
                return None

            metrics = _bar_series_metrics(bars)
            if metrics is None:
                return None
            first_price, last_price, vol, provenance = metrics

            move_pct = ((last_price - first_price) / first_price) * 100.0
            is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
            net = self.bridge.calculate_net_profit(abs(move_pct))

            # Coherence weight from change within last 5 bars (stability)
            last5 = bars[-5:] if len(bars) >= 5 else bars
            highs = [_required_number(bar, "h", "high", positive=True) for bar in last5]
            lows = [_required_number(bar, "l", "low", positive=True) for bar in last5]
            if any(value is None for value in highs + lows):
                return None
            observed_highs = [value for value in highs if value is not None]
            observed_lows = [value for value in lows if value is not None]
            observed_range = max(observed_highs) - min(observed_lows)
            coherence = 1.0 if observed_range == 0 else 1.0 / (1.0 + observed_range)

            # Only consider profitable opportunities
            if not is_profitable:
                return None

            score = abs(move_pct) * math.log(1 + vol + 1.0) * (coherence * 2.0)
            side = 'buy' if move_pct < 0 else 'sell'
            opp = AnimalOpportunity(
                symbol=sym,
                side=side,
                move_pct=move_pct,
                net_pct=net,
                volume=vol,
                reason=f"Lion ({tier})",
                **provenance,
            )
            return score, opp
        except Exception:
            return None

    def hunt(self, limit: int = 10) -> List[AnimalOpportunity]:
        symbols = self._get_crypto_universe()
        
        # 🚀 BATCH: Get all bars in ONE call (or from cache)
        all_bars = self._get_all_bars_batched(symbols, limit=24)
        
        scored = []
        for s in symbols:
            bars = all_bars.get(s, [])
            r = self.score_symbol(s, bars)
            if r:
                scored.append(r)
        scored.sort(key=lambda x: -x[0])
        return [opp for _, opp in scored[:limit]]


class AlpacaArmyAnts(BaseAnimalScanner):
    """Forage for small profits across many liquid pairs.

    - Targets small moves (>= valid threshold) with high liquidity
    - Returns small allocation opportunities
    
    🚀 V2: Uses batch cached data - ZERO individual API calls!
    """

    def forage(self, max_targets: int = 20) -> List[AnimalOpportunity]:
        symbols = self._get_crypto_universe()
        results: List[AnimalOpportunity] = []
        
        # 🚀 BATCH: Get all bars in ONE call (or from cache)
        all_bars = self._get_all_bars_batched(symbols, limit=6)

        for sym in symbols:
            try:
                bars = all_bars.get(sym, [])
                if not bars or len(bars) < 1:
                    continue

                metrics = _bar_series_metrics(bars)
                if metrics is None:
                    continue
                first_price, last_price, vol, provenance = metrics

                move_pct = ((last_price - first_price) / first_price) * 100.0
                is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                net = self.bridge.calculate_net_profit(abs(move_pct))

                # Ants prefer small valid opportunities with big volume
                if is_profitable and abs(move_pct) <= (self.bridge.get_cost_thresholds().tier_1_hot_threshold * 1.5):
                    side = 'buy' if move_pct < 0 else 'sell'
                    results.append(
                        AnimalOpportunity(
                            symbol=sym,
                            side=side,
                            move_pct=move_pct,
                            net_pct=net,
                            volume=vol,
                            reason=f"Ant (tier={tier})",
                            **provenance,
                        )
                    )

            except Exception:
                continue

        results.sort(key=lambda x: -x.volume)
        return results[:max_targets]


class AlpacaHummingbird(BaseAnimalScanner):
    """Micro-rotation pollinator: rapid scalps on high-frequency momentum.

    Focuses on short-term (6h) momentum with tight profit targets.
    Best for catching quick reversals and micro-swings.
    
    🚀 V2: Uses batch cached data - ZERO individual API calls!
    """

    def pollinate(self, limit: int = 12) -> List[AnimalOpportunity]:
        symbols = self._get_crypto_universe()
        results: List[AnimalOpportunity] = []
        
        # 🚀 BATCH: Get all bars in ONE call (or from cache)
        all_bars = self._get_all_bars_batched(symbols, limit=6)

        for s in symbols:
            try:
                bars = all_bars.get(s, [])
                if not bars or len(bars) < 1:
                    continue

                metrics = _bar_series_metrics(bars)
                if metrics is None:
                    continue
                first_price, last_price, vol, provenance = metrics

                move_pct = ((last_price - first_price) / first_price) * 100.0

                is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                net = self.bridge.calculate_net_profit(abs(move_pct))

                # Hummingbird prefers quick, moderate moves (not extreme)
                thresholds = self.bridge.get_cost_thresholds()
                max_move = thresholds.tier_1_hot_threshold * 2.0  # Cap at 2x HOT
                if is_profitable and abs(move_pct) <= max_move:
                    side = 'buy' if move_pct < 0 else 'sell'
                    results.append(AnimalOpportunity(
                        symbol=s, side=side, move_pct=move_pct,
                        net_pct=net, volume=vol, reason=f"Hummingbird ({tier})",
                        **provenance,
                    ))
            except Exception:
                continue

        # Sort by net profit (best micro-trades first)
        results.sort(key=lambda x: -x.net_pct)
        return results[:limit]


class AlpacaSwarmOrchestrator:
    """Coordinates animal agents and can execute trades via trailing stops.
    
    🚀 V2: Uses BATCH API calls - one call serves ALL 4 animal scanners!
    Data priority: Binance WS cache → Kraken cache → Alpaca batch API
    """

    def __init__(self, alpaca: AlpacaClient, bridge: AlpacaScannerBridge):
        self.alpaca = alpaca
        self.bridge = bridge
        self.wolf = AlpacaLoneWolf(alpaca, bridge)
        self.lion = AlpacaLionHunt(alpaca, bridge)
        self.ants = AlpacaArmyAnts(alpaca, bridge)
        self.hummingbird = AlpacaHummingbird(alpaca, bridge)
        self.dry_run = False  # Stage AD: live default. Opt out by passing dry_run=True at construction or AUREON_DRY_RUN=true env override.

        # 🔗 Communication Buses
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = get_chirp_bus() if CHIRP_BUS_AVAILABLE else None

    def run_once(self) -> Dict[str, List[AnimalOpportunity]]:
        """Run one orchestration cycle (dry-run safe).

        Returns a dict with results from each agent.
        
        🚀 V2: All agents share the SAME cached batch data!
        """
        logger.info("Orchestrator: running single pass")
        
        # Check what data source will be used
        global _BATCH_BARS_CACHE, _BATCH_CACHE_TIME
        if _BATCH_BARS_CACHE and (time.time() - _BATCH_CACHE_TIME) < _BATCH_CACHE_TTL:
            logger.info(f"🎯 Using existing batch cache ({len(_BATCH_BARS_CACHE)} symbols)")
        else:
            # Check external caches
            binance_cache = _read_external_cache('binance_ws_cache.json', max_age=120)
            kraken_cache = _read_external_cache('kraken_market_cache.json', max_age=120)
            if binance_cache:
                logger.info("🟡 Binance WS cache available - ZERO Alpaca API calls!")
            elif kraken_cache:
                logger.info("🐙 Kraken cache available - ZERO Alpaca API calls!")
            else:
                logger.info("🦙 Will use Alpaca batch API (1 call for all symbols)")
        
        out = {}
        out['wolf'] = self.wolf.find_targets(limit=8)
        out['lion'] = self.lion.hunt(limit=8)
        out['ants'] = self.ants.forage(max_targets=12)
        out['hummingbird'] = self.hummingbird.pollinate(limit=12)

        # Notify bridge of opportunities detected
        total = sum(len(v) for v in out.values())
        self.bridge._stats['opportunities_detected'] += total
        
        # 🔊 Publish to Hive Mind
        self._publish_opportunities(out)
        
        return out

    def _publish_opportunities(self, results: Dict[str, List[AnimalOpportunity]]):
        """Publish opportunities to Hive Mind."""
        if not self.thought_bus and not self.chirp_bus:
            return

        for agent, opps in results.items():
            for opp in opps:
                # ThoughtBus
                if self.thought_bus:
                    try:
                        self.thought_bus.publish(Thought(
                            source=f"animal_momentum.{agent}",
                            topic="opportunity.momentum",
                            payload={
                                'symbol': opp.symbol, 
                                'side': opp.side, 
                                'move_pct': opp.move_pct, 
                                'net_pct': opp.net_pct, 
                                'reason': opp.reason,
                                'volume': opp.volume,
                                'agent': agent,
                                'truth_status': opp.truth_status,
                                'source_id': opp.source_id,
                                'source_timestamp': opp.source_timestamp,
                                'received_at': opp.received_at,
                                'generated_values': opp.generated_values,
                                'eligible_for_external_action': opp.eligible_for_external_action,
                            }
                        ))
                    except: pass
                
                # ChirpBus (only for top opportunities)
                if self.chirp_bus and opp.net_pct > 0.4:
                    try:
                        self.chirp_bus.emit_message(
                            message=f"{agent.upper()} {opp.symbol} {opp.net_pct:.2f}%",
                            direction=ChirpDirection.UP if opp.side == 'buy' else ChirpDirection.DOWN,
                            confidence=min(1.0, opp.net_pct / 2.0),
                            symbol=opp.symbol,
                            frequency=600.0 if opp.side=='buy' else 300.0,
                            message_type=ChirpType.OPPORTUNITY
                        )
                    except: pass

    def execute_opportunity(self, opp: AnimalOpportunity, qty: float, use_trailing_stop: bool = True) -> Optional[Dict]:
        """Execute a trade for an opportunity with optional trailing stop.

        Args:
            opp: The opportunity to execute
            qty: Quantity to trade
            use_trailing_stop: Whether to use trailing stop (default True)

        Returns:
            Order result dict or None if dry-run / error
        """
        now = time.time()
        source_timestamp = _finite_float(opp.source_timestamp, positive=True)
        received_at = _finite_float(opp.received_at, positive=True)
        requested_qty = _finite_float(qty, positive=True)
        if (
            opp.truth_status not in {"live", "real_derived"}
            or not opp.source_id
            or source_timestamp is None
            or received_at is None
            or requested_qty is None
            or now - source_timestamp > MAX_LATEST_BAR_AGE_SECONDS
            or source_timestamp - now > MAX_SOURCE_CLOCK_SKEW_SECONDS
            or received_at - source_timestamp > MAX_LATEST_BAR_AGE_SECONDS
            or opp.generated_values is not False
            or opp.eligible_for_external_action is not True
        ):
            logger.warning("Blocked %s: source evidence unavailable or stale", opp.symbol)
            return {
                "status": "blocked",
                "truth_status": "no_data",
                "decision_status": "denied",
                "reason": "signal_evidence_unavailable_or_stale",
                "provider_order_id": None,
                "filled_qty": None,
                "filled_avg_price": None,
                "eligible_for_learning": False,
                "generated_values": False,
            }

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute {opp.side} {qty} {opp.symbol} ({opp.reason})")
            return {
                "status": "not_submitted",
                "truth_status": "dry_run",
                "decision_status": "not_submitted",
                "dry_run": True,
                "symbol": opp.symbol,
                "side": opp.side,
                "requested_qty": requested_qty,
                "provider_order_id": None,
                "filled_qty": None,
                "filled_avg_price": None,
                "eligible_for_learning": False,
                "generated_values": False,
            }

        try:
            if use_trailing_stop:
                result = self.bridge.execute_with_trailing_stop(
                    symbol=opp.symbol,
                    side=opp.side,
                    qty=requested_qty,
                    trail_percent=2.0  # Default 2% trail
                )
            else:
                result = self.alpaca.place_market_order(opp.symbol, opp.side, requested_qty)

            if not isinstance(result, dict):
                return {
                    "status": "submitted_unverified",
                    "truth_status": "no_data",
                    "decision_status": "reconciliation_required",
                    "reason": "provider_response_not_mapping",
                    "provider_order_id": None,
                    "eligible_for_learning": False,
                    "generated_values": False,
                }
            provider_order_id = (
                result.get("id")
                or result.get("order_id")
                or result.get("orderId")
                or result.get("client_order_id")
            )
            if not provider_order_id:
                logger.error("Order response for %s lacks a provider order id", opp.symbol)
                return {
                    "status": "submitted_unverified",
                    "truth_status": "no_data",
                    "decision_status": "reconciliation_required",
                    "reason": "provider_order_id_missing",
                    "provider_order_id": None,
                    "eligible_for_learning": False,
                    "generated_values": False,
                }
            logger.info(f"Submitted {opp.side} {requested_qty} {opp.symbol}: provider_order_id={provider_order_id}")
            return {
                **result,
                "status": "submitted",
                "truth_status": "live",
                "decision_status": "submitted",
                "provider_order_id": str(provider_order_id),
                "eligible_for_learning": False,
                "generated_values": False,
            }
        except Exception as e:
            logger.error(f"Execution failed for {opp.symbol}: {e}")
            return None

    def get_best_opportunity(self) -> Optional[AnimalOpportunity]:
        """Get the single best opportunity across all agents."""
        results = self.run_once()
        all_opps = []
        for agent_opps in results.values():
            all_opps.extend(agent_opps)

        if not all_opps:
            return None

        # Sort by net profit
        all_opps.sort(key=lambda x: -x.net_pct)
        return all_opps[0]


def main(dry_run: bool = True):
    alpaca = AlpacaClient()
    fee_tracker = AlpacaFeeTracker(alpaca)
    bridge = AlpacaScannerBridge(alpaca_client=alpaca, fee_tracker=fee_tracker, enable_sse=False, enable_stocks=False)

    orch = AlpacaSwarmOrchestrator(alpaca, bridge)
    results = orch.run_once()

    print("\n=== SWARM SUMMARY ===")
    for k, v in results.items():
        print(f"\n{k.upper()}: {len(v)} targets")
        for i, opp in enumerate(v[:8], 1):
            print(f" {i:2}. {opp.symbol:12} {opp.side:4} {opp.move_pct:+6.2f}% net {opp.net_pct:+.3f}% {opp.reason}")

    print("\n✅ Swarm pass complete (dry-run: %s)" % str(dry_run))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
    main(dry_run=True)


# ═══════════════════════════════════════════════════════════════
# 🔌 INTEGRATION API - Wrapper for Orca Complete Kill Cycle
# ═══════════════════════════════════════════════════════════════

class AnimalMomentumScanners:
    """Unified interface for all animal momentum scanners (no client deps)."""
    
    def __init__(self):
        self.wolf = None
        self.lion = None
        self.ants = None
        self.hummingbird = None
        self.orchestrator = None
        
        # Try to initialize with clients if available
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            from aureon.bridges.aureon_alpaca_scanner_bridge import AlpacaScannerBridge
            
            alpaca = AlpacaClient()
            bridge = AlpacaScannerBridge(alpaca)
            
            self.wolf = AlpacaLoneWolf(alpaca, bridge)
            self.lion = AlpacaLionHunt(alpaca, bridge)
            self.ants = AlpacaArmyAnts(alpaca, bridge)
            self.hummingbird = AlpacaHummingbird(alpaca, bridge)
            self.orchestrator = AlpacaSwarmOrchestrator(alpaca, bridge)
            
            print("🦅 Animal Momentum Scanners: FULLY INITIALIZED")
            print("   🐺 Wolf (24h breakout)")
            print("   🦁 Lion (composite scorer)")
            print("   🐜 Ants (high-frequency)")
            print("   🐦 Hummingbird (micro-scalp)")
        except Exception as e:
            print(f"🦅 Animal Momentum Scanners: LITE MODE (no exchange client)")
            print(f"   ⚠️ {str(e)[:50]}")
    
    def get_all_signals(self) -> dict:
        """Get signals from all animal scanners."""
        signals = {}
        
        if self.wolf:
            try:
                signals['wolf'] = self.wolf.scan()
            except Exception as e:
                signals['wolf'] = {'error': str(e)}
        
        if self.lion:
            try:
                signals['lion'] = self.lion.scan()
            except Exception as e:
                signals['lion'] = {'error': str(e)}
        
        if self.ants:
            try:
                signals['ants'] = self.ants.scan()
            except Exception as e:
                signals['ants'] = {'error': str(e)}
        
        if self.hummingbird:
            try:
                signals['hummingbird'] = self.hummingbird.scan()
            except Exception as e:
                signals['hummingbird'] = {'error': str(e)}
        
        return signals
    
    def run_swarm(self, max_positions: int = 3, capital: float = 100.0):
        """Run the full swarm orchestrator."""
        if self.orchestrator:
            return self.orchestrator.run_swarm_cycle(max_positions, capital)
        return {'error': 'Orchestrator not available'}

_GLOBAL_INSTANCE = None

def get_animal_scanners():
    """Get or create global animal scanners instance."""
    global _GLOBAL_INSTANCE
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = AnimalMomentumScanners()
    return _GLOBAL_INSTANCE



# ═══════════════════════════════════════════════════════════════
# 🔌 INTEGRATION API - Wrapper for Orca Complete Kill Cycle
# ═══════════════════════════════════════════════════════════════

class AnimalMomentumScanners:
    """Unified interface for all animal momentum scanners (no client deps)."""
    
    def __init__(self):
        self.wolf = None
        self.lion = None
        self.ants = None
        self.hummingbird = None
        self.orchestrator = None
        
        # Try to initialize with clients if available
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            from aureon.bridges.aureon_alpaca_scanner_bridge import AlpacaScannerBridge
            
            alpaca = AlpacaClient()
            bridge = AlpacaScannerBridge(alpaca)
            
            self.wolf = AlpacaLoneWolf(alpaca, bridge)
            self.lion = AlpacaLionHunt(alpaca, bridge)
            self.ants = AlpacaArmyAnts(alpaca, bridge)
            self.hummingbird = AlpacaHummingbird(alpaca, bridge)
            self.orchestrator = AlpacaSwarmOrchestrator(alpaca, bridge)
            
            print("🦅 Animal Momentum Scanners: FULLY INITIALIZED")
            print("   🐺 Wolf (24h breakout)")
            print("   🦁 Lion (composite scorer)")
            print("   🐜 Ants (high-frequency)")
            print("   🐦 Hummingbird (micro-scalp)")
        except Exception as e:
            print(f"🦅 Animal Momentum Scanners: LITE MODE (no exchange client)")
            print(f"   ⚠️ {str(e)[:50]}")
    
    def get_all_signals(self) -> dict:
        """Get signals from all animal scanners."""
        signals = {}
        
        if self.wolf:
            try:
                signals['wolf'] = self.wolf.scan()
            except Exception as e:
                signals['wolf'] = {'error': str(e)}
        
        if self.lion:
            try:
                signals['lion'] = self.lion.scan()
            except Exception as e:
                signals['lion'] = {'error': str(e)}
        
        if self.ants:
            try:
                signals['ants'] = self.ants.scan()
            except Exception as e:
                signals['ants'] = {'error': str(e)}
        
        if self.hummingbird:
            try:
                signals['hummingbird'] = self.hummingbird.scan()
            except Exception as e:
                signals['hummingbird'] = {'error': str(e)}
        
        return signals
    
    def run_swarm(self, max_positions: int = 3, capital: float = 100.0):
        """Run the full swarm orchestrator."""
        if self.orchestrator:
            return self.orchestrator.run_swarm_cycle(max_positions, capital)
        return {'error': 'Orchestrator not available'}

_GLOBAL_INSTANCE = None

def get_animal_scanners():
    """Get or create global animal scanners instance."""
    global _GLOBAL_INSTANCE
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = AnimalMomentumScanners()
    return _GLOBAL_INSTANCE
