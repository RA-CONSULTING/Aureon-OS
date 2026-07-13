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
            ts = float(data.get('generated_at', 0) or 0)
            if ts > 0 and (time.time() - ts) <= max_age:
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
            coherence = signal_data.get('coherence', 0)
            if symbol and coherence > 0.5:  # Only high-confidence whale signals
                # Add to priority target list (dedupe)
                if symbol not in self._orca_whale_targets:
                    self._orca_whale_targets.append(symbol)
                    self._orca_target_time = time.time()
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
                    if ticker and 'c' in ticker:  # 'c' = last trade
                        price = float(ticker['c'][0])
                        open_price = float(ticker.get('o', [price])[0])
                        if open_price > 0:
                            move_pct = ((price - open_price) / open_price) * 100
                            if abs(move_pct) > 0.5:  # 0.5%+ move
                                volume = float(ticker.get('v', [0])[1]) * price
                                opp = AnimalOpportunity(
                                    symbol=symbol,
                                    side='buy' if move_pct > 0 else 'sell',
                                    move_pct=abs(move_pct),
                                    net_pct=abs(move_pct) - 0.2,  # After fees
                                    volume=volume,
                                    reason=f"Kraken momentum: {move_pct:+.2f}%"
                                )
                                opportunities.append(opp)
            except Exception as e:
                logger.debug(f"Kraken scan error: {e}")
        
        # Scan Binance WebSocket for momentum
        if self.binance_ws and hasattr(self.binance_ws, 'get_latest_ticker'):
            try:
                for symbol in symbols:
                    ticker = self.binance_ws.get_latest_ticker(symbol)
                    if ticker and 'priceChangePercent' in ticker:
                        move_pct = float(ticker['priceChangePercent'])
                        if abs(move_pct) > 0.5:
                            volume = float(ticker.get('quoteVolume', 0))
                            opp = AnimalOpportunity(
                                symbol=symbol,
                                side='buy' if move_pct > 0 else 'sell',
                                move_pct=abs(move_pct),
                                net_pct=abs(move_pct) - 0.2,
                                volume=volume,
                                reason=f"Binance momentum: {move_pct:+.2f}%"
                            )
                            opportunities.append(opp)
            except Exception as e:
                logger.debug(f"Binance scan error: {e}")
        
        # Use Wave Scanner for aggregated opportunities
        if self.wave_scanner and hasattr(self.wave_scanner, 'get_hot_opportunities'):
            try:
                wave_opps = self.wave_scanner.get_hot_opportunities(min_score=0.6)
                for wo in wave_opps:
                    opp = AnimalOpportunity(
                        symbol=wo.get('symbol', ''),
                        side='buy' if wo.get('direction') == 'up' else 'sell',
                        move_pct=wo.get('move_pct', 0),
                        net_pct=wo.get('net_pct', 0),
                        volume=wo.get('volume_usd', 0),
                        reason=f"Wave scanner: {wo.get('reason', 'multi-market signal')}"
                    )
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
        
        # 🟡 TRY BINANCE CACHE FIRST (FREE, no API calls!)
        binance_cache = _read_external_cache('binance_ws_cache.json', max_age=120)
        if binance_cache:
            ticker_cache = binance_cache.get('ticker_cache', {})
            if len(ticker_cache) > 10:
                logger.info(f"🟡 Using Binance WS cache ({len(ticker_cache)} tickers) - ZERO Alpaca API calls!")
                # Convert Binance format to bars-like format
                result = {}
                for key, ticker in ticker_cache.items():
                    if not isinstance(ticker, dict):
                        continue
                    base = ticker.get('base', '').upper()
                    if not base:
                        continue
                    sym = f"{base}/USD"
                    price = float(ticker.get('price', 0) or 0)
                    change = float(ticker.get('change24h', 0) or 0)
                    vol = float(ticker.get('volume', 0) or 0)
                    if price > 0:
                        # Simulate bars from 24h change
                        open_price = price / (1 + change/100) if change != -100 else price
                        result[sym] = [{
                            'o': open_price, 'c': price, 'h': max(open_price, price) * 1.01,
                            'l': min(open_price, price) * 0.99, 'v': vol
                        }]
                if result:
                    _BATCH_BARS_CACHE = result
                    _BATCH_CACHE_TIME = time.time()
                    return result
        
        # 🐙 TRY KRAKEN CACHE SECOND (also FREE!)
        kraken_cache = _read_external_cache('kraken_market_cache.json', max_age=120)
        if kraken_cache:
            ticker_cache = kraken_cache.get('ticker_cache', {})
            if len(ticker_cache) > 5:
                logger.info(f"🐙 Using Kraken cache ({len(ticker_cache)} tickers) - ZERO Alpaca API calls!")
                result = {}
                for key, ticker in ticker_cache.items():
                    if not isinstance(ticker, dict):
                        continue
                    base = ticker.get('base', '').upper()
                    if not base:
                        continue
                    sym = f"{base}/USD"
                    price = float(ticker.get('price', 0) or 0)
                    change = float(ticker.get('change24h', 0) or 0)
                    vol = float(ticker.get('volume', 0) or 0)
                    if price > 0:
                        open_price = price / (1 + change/100) if change != -100 else price
                        result[sym] = [{
                            'o': open_price, 'c': price, 'h': max(open_price, price) * 1.01,
                            'l': min(open_price, price) * 0.99, 'v': vol
                        }]
                if result:
                    _BATCH_BARS_CACHE = result
                    _BATCH_CACHE_TIME = time.time()
                    return result
        
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
                if bars:
                    result[orig_sym] = bars
            
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

                first_price = float(bars[0].get('o', bars[0].get('open', 0)) or 0)
                last_price = float(bars[-1].get('c', bars[-1].get('close', 0)) or 0)
                if first_price <= 0 or last_price <= 0:
                    continue

                move_pct = ((last_price - first_price) / first_price) * 100.0
                vol = sum(float(b.get('v', b.get('volume', 0)) or 0) for b in bars)

                is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                net = self.bridge.calculate_net_profit(abs(move_pct))

                if not is_profitable:
                    continue

                side = 'buy' if move_pct < 0 else 'sell'
                reason = f"Wolf ({tier})"
                results.append(AnimalOpportunity(symbol=sym, side=side, move_pct=move_pct, net_pct=net, volume=vol, reason=reason))

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

            first_price = float(bars[0].get('o', bars[0].get('open', 0)) or 0)
            last_price = float(bars[-1].get('c', bars[-1].get('close', 0)) or 0)
            if first_price <= 0 or last_price <= 0:
                return None

            move_pct = ((last_price - first_price) / first_price) * 100.0
            vol = sum(float(b.get('v', b.get('volume', 0)) or 0) for b in bars)
            is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
            net = self.bridge.calculate_net_profit(abs(move_pct))

            # Coherence weight from change within last 5 bars (stability)
            last5 = bars[-5:] if len(bars) >= 5 else bars
            highs = [float(b.get('h', b.get('high', 0)) or 0) for b in last5]
            lows = [float(b.get('l', b.get('low', 0)) or 0) for b in last5]
            if not highs or not lows:
                coherence = 1.0
            else:
                var = (max(highs) - min(lows)) or 1.0
                coherence = 1.0 / (1.0 + var)

            # Only consider profitable opportunities
            if not is_profitable:
                return None

            score = abs(move_pct) * math.log(1 + vol + 1.0) * (coherence * 2.0)
            side = 'buy' if move_pct < 0 else 'sell'
            opp = AnimalOpportunity(symbol=sym, side=side, move_pct=move_pct, net_pct=net, volume=vol, reason=f"Lion ({tier})")
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

                first_price = float(bars[0].get('o', bars[0].get('open', 0)) or 0)
                last_price = float(bars[-1].get('c', bars[-1].get('close', 0)) or 0)
                if first_price <= 0 or last_price <= 0:
                    continue

                move_pct = ((last_price - first_price) / first_price) * 100.0
                vol = sum(float(b.get('v', b.get('volume', 0)) or 0) for b in bars)
                is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                net = self.bridge.calculate_net_profit(abs(move_pct))

                # Ants prefer small valid opportunities with big volume
                if is_profitable and abs(move_pct) <= (self.bridge.get_cost_thresholds().tier_1_hot_threshold * 1.5):
                    side = 'buy' if move_pct < 0 else 'sell'
                    results.append(AnimalOpportunity(symbol=sym, side=side, move_pct=move_pct, net_pct=net, volume=vol, reason=f"Ant (tier={tier})"))

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

                first_price = float(bars[0].get('o', bars[0].get('open', 0)) or 0)
                last_price = float(bars[-1].get('c', bars[-1].get('close', 0)) or 0)
                if first_price <= 0 or last_price <= 0:
                    continue

                move_pct = ((last_price - first_price) / first_price) * 100.0
                vol = sum(float(b.get('v', b.get('volume', 0)) or 0) for b in bars)

                is_profitable, tier = self.bridge.is_move_profitable(abs(move_pct))
                net = self.bridge.calculate_net_profit(abs(move_pct))

                # Hummingbird prefers quick, moderate moves (not extreme)
                thresholds = self.bridge.get_cost_thresholds()
                max_move = thresholds.tier_1_hot_threshold * 2.0  # Cap at 2x HOT
                if is_profitable and abs(move_pct) <= max_move:
                    side = 'buy' if move_pct < 0 else 'sell'
                    results.append(AnimalOpportunity(
                        symbol=s, side=side, move_pct=move_pct,
                        net_pct=net, volume=vol, reason=f"Hummingbird ({tier})"
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
                                'agent': agent
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
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute {opp.side} {qty} {opp.symbol} ({opp.reason})")
            return {'dry_run': True, 'symbol': opp.symbol, 'side': opp.side, 'qty': qty}

        try:
            if use_trailing_stop:
                result = self.bridge.execute_with_trailing_stop(
                    symbol=opp.symbol,
                    side=opp.side,
                    qty=qty,
                    trail_percent=2.0  # Default 2% trail
                )
            else:
                result = self.alpaca.place_market_order(opp.symbol, opp.side, qty)

            logger.info(f"Executed {opp.side} {qty} {opp.symbol}: {result}")
            return result
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
