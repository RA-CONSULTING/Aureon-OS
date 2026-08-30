#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌊 AUREON OCEAN SCANNER - BE A TURTLE IN THE SEA OF POSSIBILITIES
═════════════════════════════════════════════════════════════════

"Why be a big fish in a small pond when you can be a turtle in the ocean?"
                                                        - Gary Leckey

This module scans the ENTIRE global market, not just what we hold.
It identifies opportunities BEFORE we need to hold them.

UNIVERSE EXPANSION:
  • Kraken: 1,434 tradeable pairs
  • Alpaca Crypto: 62 symbols  
  • Alpaca Stocks: 10,000+ symbols (when market open)
  • Binance: 2,000+ pairs
  • TOTAL POTENTIAL: 13,000+ opportunities!

vs our current "puddle":
  • 28 opportunities (only from 5 held positions)

"""
import os

import asyncio
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime, timedelta
import json
import logging
import aiohttp  # For open source API calls

# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 OPEN SOURCE DATA FEEDS (NO API KEYS REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════
OPEN_SOURCE_FEEDS = {
    'coingecko': 'https://api.coingecko.com/api/v3',
    'binance_public': 'https://api.binance.com/api/v3',
    'kraken_public': 'https://api.kraken.com/0/public',
}

# Optional Capital.com stock feed (off by default)
try:
    from aureon.exchanges.capital_client import CapitalClient
except Exception:
    CapitalClient = None

# 🚌 Communication Buses
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None

try:
    from aureon.core.aureon_chirp_bus import ChirpBus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False
    ChirpBus = None

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden ratio
LOVE_FREQUENCY = 528
SCHUMANN_BASE = 7.83

logger = logging.getLogger(__name__)

@dataclass
class OceanOpportunity:
    """A single opportunity in the ocean of possibilities."""
    symbol: str
    exchange: str
    opportunity_type: str  # 'momentum', 'arbitrage', 'reversal', 'breakout'
    
    # Price data
    current_price: float = 0.0
    price_24h_ago: float = 0.0
    price_1h_ago: float = 0.0
    
    # Momentum metrics
    momentum_1m: float = 0.0  # % change per minute
    momentum_5m: float = 0.0
    momentum_1h: float = 0.0
    momentum_24h: float = 0.0
    
    # Volume metrics
    volume_24h: float = 0.0
    volume_ratio: float = 1.0  # Current vs average
    
    # Scoring
    ocean_score: float = 0.0  # 0-1 overall opportunity score
    confidence: float = 0.0
    expected_pnl: float = 0.0
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'type': self.opportunity_type,
            'price': self.current_price,
            'momentum_1m': self.momentum_1m,
            'momentum_1h': self.momentum_1h,
            'momentum_24h': self.momentum_24h,
            'volume_ratio': self.volume_ratio,
            'ocean_score': self.ocean_score,
            'confidence': self.confidence,
            'expected_pnl': self.expected_pnl,
            'reason': self.reason,
        }


class OceanScanner:
    """
    🌊 THE OCEAN SCANNER - Scans the entire global market.
    
    Instead of only looking at what we hold (puddle mentality),
    we scan EVERYTHING and find the best opportunities first,
    THEN decide what to hold.
    
    "The turtle doesn't just look at the coral reef it's sitting on.
     It looks at the entire ocean and swims to where the food is."
    """
    
    def __init__(self, exchanges: Dict = None):
        self.exchanges = exchanges or {}
        
        # Bus Integration
        self.thought_bus = ThoughtBus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE:
            try:
                self.chirp_bus = ChirpBus()
            except Exception:
                pass

        # Optional stock scanning configuration
        self.scan_alpaca_stocks = os.getenv('AUREON_SCAN_ALPACA_STOCKS', '0') == '1'
        self.stock_data_provider = os.getenv('AUREON_STOCK_DATA_PROVIDER', 'capital').lower().strip() or 'capital'
        self.capital_stock_cache_path = os.getenv('CAPITAL_STOCK_CACHE_PATH', 'ws_cache/capital_stocks.json')
        self.capital_stock_cache_max_age_s = float(os.getenv('CAPITAL_STOCK_CACHE_MAX_AGE_S', '10'))
        self.stock_validate_top_n = int(os.getenv('AUREON_STOCK_VALIDATE_TOP_N', '20'))
        self.capital_client = None

        # ═══════════════════════════════════════════════════════════════════
        # 🟡 BINANCE → ALPACA CRYPTO SCANNING (use free Binance WS to scan,
        #    then validate/execute on Alpaca; keeps Alpaca API usage minimal)
        # ═══════════════════════════════════════════════════════════════════
        self.scan_alpaca_crypto_via_binance = os.getenv('AUREON_SCAN_ALPACA_CRYPTO_VIA_BINANCE', '1') == '1'
        self.binance_ws_cache_path = os.getenv('WS_PRICE_CACHE_PATH', 'ws_cache/ws_prices.json')
        self.binance_ws_cache_max_age_s = float(os.getenv('WS_PRICE_CACHE_MAX_AGE_S', '10'))
        self.alpaca_crypto_validate_top_n = int(os.getenv('AUREON_ALPACA_CRYPTO_VALIDATE_TOP_N', '30'))
        # Mapping: Alpaca crypto base (BTC) -> Binance symbol (BTCUSDT)
        self._alpaca_to_binance_map: Dict[str, str] = {}
        
        # Universe tracking
        self.kraken_universe: Set[str] = set()
        self.alpaca_crypto_universe: Set[str] = set()
        self.alpaca_stock_universe: Set[str] = set()
        self.binance_universe: Set[str] = set()
        
        # ═══════════════════════════════════════════════════════════════════
        # 🌐 OPEN SOURCE UNIVERSE (NO API KEYS NEEDED!)
        # ═══════════════════════════════════════════════════════════════════
        self.coingecko_universe: Set[str] = set()      # 14,000+ coins (FREE)
        self.binance_public_universe: Set[str] = set() # 1,495+ pairs (NO KEY)
        self.kraken_public_universe: Set[str] = set()  # 800+ pairs (NO KEY)
        self.open_source_prices: Dict[str, Dict] = {}  # Cached prices from free APIs
        
        # Price cache
        self.prices: Dict[str, Dict] = {}  # symbol -> {price, timestamp, exchange}
        
        # Momentum tracking
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}  # symbol -> [(timestamp, price)]
        self.momentum_cache: Dict[str, Dict] = {}  # symbol -> {1m, 5m, 1h, 24h}
        
        # Opportunity pools
        self.hot_opportunities: List[OceanOpportunity] = []
        self.arbitrage_opportunities: List[OceanOpportunity] = []
        self.momentum_opportunities: List[OceanOpportunity] = []
        
        # Statistics
        self.total_symbols_scanned = 0
        self.last_scan_time = 0
        self.scan_count = 0
        
        print("🌊 OCEAN SCANNER INITIALIZED")
        print("   Ready to scan the SEA of possibilities!")
        
    async def discover_universe(self) -> Dict[str, int]:
        """
        🔭 DISCOVER THE ENTIRE TRADING UNIVERSE
        
        This scans all exchanges and builds a map of every tradeable
        symbol across the global market.
        """
        print("\n" + "=" * 70)
        print("🔭 DISCOVERING THE TRADING UNIVERSE...")
        print("=" * 70)
        
        universe_counts = {}
        
        # ═══════════════════════════════════════════════════════════════
        # 🐙 KRAKEN UNIVERSE
        # ═══════════════════════════════════════════════════════════════
        if 'kraken' in self.exchanges:
            try:
                kraken = self.exchanges['kraken']
                if hasattr(kraken, '_load_asset_pairs'):
                    pairs = kraken._load_asset_pairs()
                    self.kraken_universe = {p for p in pairs.keys() if not p.endswith('.d')}
                    universe_counts['kraken'] = len(self.kraken_universe)
                    print(f"   🐙 KRAKEN: {len(self.kraken_universe)} pairs discovered!")
            except Exception as e:
                print(f"   ❌ Kraken discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 🦙 ALPACA CRYPTO UNIVERSE
        # ═══════════════════════════════════════════════════════════════
        if 'alpaca' in self.exchanges:
            try:
                alpaca = self.exchanges['alpaca']
                if hasattr(alpaca, 'get_tradable_crypto_symbols'):
                    symbols = alpaca.get_tradable_crypto_symbols() or []
                    self.alpaca_crypto_universe = set(symbols)
                    universe_counts['alpaca_crypto'] = len(self.alpaca_crypto_universe)
                    print(f"   🦙 ALPACA CRYPTO: {len(self.alpaca_crypto_universe)} symbols discovered!")
            except Exception as e:
                print(f"   ❌ Alpaca crypto discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 📈 ALPACA STOCKS UNIVERSE
        # ═══════════════════════════════════════════════════════════════
        if 'alpaca' in self.exchanges:
            try:
                alpaca = self.exchanges['alpaca']
                # Check for trading API
                if hasattr(alpaca, '_trading_api'):
                    api = alpaca._trading_api
                elif hasattr(alpaca, 'trading_client'):
                    api = alpaca.trading_client
                else:
                    api = None
                
                if api and hasattr(api, 'get_all_assets'):
                    from alpaca.trading.requests import GetAssetsRequest
                    from alpaca.trading.enums import AssetClass, AssetStatus
                    
                    request = GetAssetsRequest(
                        asset_class=AssetClass.US_EQUITY,
                        status=AssetStatus.ACTIVE
                    )
                    assets = api.get_all_assets(request)
                    tradeable = [a for a in assets if a.tradable and a.fractionable]
                    self.alpaca_stock_universe = {a.symbol for a in tradeable}
                    universe_counts['alpaca_stocks'] = len(self.alpaca_stock_universe)
                    print(f"   📈 ALPACA STOCKS: {len(self.alpaca_stock_universe)} symbols discovered!")
            except Exception as e:
                print(f"   ❌ Alpaca stocks discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 🟡 BINANCE UNIVERSE
        # ═══════════════════════════════════════════════════════════════
        if 'binance' in self.exchanges:
            try:
                binance = self.exchanges['binance']
                if hasattr(binance, 'exchange_info'):
                    info = binance.exchange_info()
                    symbols = info.get('symbols', [])
                    self.binance_universe = {
                        s['symbol'] for s in symbols 
                        if s.get('status') == 'TRADING' and s.get('isSpotTradingAllowed', True)
                    }
                    universe_counts['binance'] = len(self.binance_universe)
                    print(f"   🟡 BINANCE: {len(self.binance_universe)} pairs discovered!")
            except Exception as e:
                print(f"   ❌ Binance discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 🌐 OPEN SOURCE: COINGECKO (14,000+ coins - NO API KEY!)
        # ═══════════════════════════════════════════════════════════════
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{OPEN_SOURCE_FEEDS['coingecko']}/coins/list"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        coins = await resp.json()
                        self.coingecko_universe = {c['id'] for c in coins}
                        universe_counts['coingecko'] = len(self.coingecko_universe)
                        print(f"   🌐 COINGECKO: {len(self.coingecko_universe):,} coins discovered! (OPEN SOURCE)")
        except Exception as e:
            print(f"   ⚠️ CoinGecko discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 🟡 BINANCE PUBLIC API (NO API KEY - backup if client unavailable)
        # ═══════════════════════════════════════════════════════════════
        if not self.binance_universe:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{OPEN_SOURCE_FEEDS['binance_public']}/exchangeInfo"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            symbols = data.get('symbols', [])
                            self.binance_public_universe = {
                                s['symbol'] for s in symbols 
                                if s.get('status') == 'TRADING'
                            }
                            universe_counts['binance_public'] = len(self.binance_public_universe)
                            print(f"   🟡 BINANCE (PUBLIC): {len(self.binance_public_universe):,} pairs discovered! (NO API KEY)")
            except Exception as e:
                print(f"   ⚠️ Binance public discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 🐙 KRAKEN PUBLIC API (NO API KEY - backup if client unavailable)
        # ═══════════════════════════════════════════════════════════════
        if not self.kraken_universe:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{OPEN_SOURCE_FEEDS['kraken_public']}/AssetPairs"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            pairs = data.get('result', {})
                            self.kraken_public_universe = {p for p in pairs.keys() if not p.endswith('.d')}
                            universe_counts['kraken_public'] = len(self.kraken_public_universe)
                            print(f"   🐙 KRAKEN (PUBLIC): {len(self.kraken_public_universe):,} pairs discovered! (NO API KEY)")
            except Exception as e:
                print(f"   ⚠️ Kraken public discovery error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 📊 UNIVERSE SUMMARY
        # ═══════════════════════════════════════════════════════════════
        total_universe = sum(universe_counts.values())
        self.total_symbols_scanned = total_universe
        
        print()
        print("=" * 70)
        print(f"🌍 TOTAL TRADING UNIVERSE: {total_universe:,} symbols!")
        print("=" * 70)
        print()
        print("   🐢 You are now a TURTLE in the SEA of possibilities!")
        print("   🐠 Not a big fish in a tiny pond of 28 opportunities...")
        print()
        
        return universe_counts
    
    async def scan_ocean(self, limit: int = 100) -> List[OceanOpportunity]:
        """
        🌊 SCAN THE ENTIRE OCEAN FOR OPPORTUNITIES
        
        This performs a full scan of all discovered symbols,
        calculating momentum and identifying opportunities.
        
        Returns the TOP opportunities sorted by score.
        """
        print(f"\n🌊 SCANNING OCEAN... (Universe: {self.total_symbols_scanned:,} symbols)")
        scan_start = time.time()
        
        opportunities = []
        
        # Scan each exchange's universe
        if self.kraken_universe and 'kraken' in self.exchanges:
            kraken_opps = await self._scan_exchange_universe(
                'kraken', 
                self.kraken_universe,
                limit=limit // 4
            )
            opportunities.extend(kraken_opps)
        
        # ═══════════════════════════════════════════════════════════════════
        # 🟡 BINANCE-POWERED ALPACA CRYPTO SCANNING (heavy lifting via free WS)
        # ═══════════════════════════════════════════════════════════════════
        if (
            self.scan_alpaca_crypto_via_binance
            and self.alpaca_crypto_universe
            and 'alpaca' in self.exchanges
        ):
            binance_alpaca_opps = await self._scan_alpaca_crypto_via_binance(limit=limit // 2)
            opportunities.extend(binance_alpaca_opps)
        elif self.alpaca_crypto_universe and 'alpaca' in self.exchanges:
            # Fallback: direct Alpaca scan (original behavior)
            alpaca_opps = await self._scan_exchange_universe(
                'alpaca',
                self.alpaca_crypto_universe,
                limit=limit // 4
            )
            opportunities.extend(alpaca_opps)

        # Optional: scan Alpaca stock universe using Capital.com as market-data provider.
        # This keeps Alpaca API usage low by only validating the best candidates.
        if (
            self.scan_alpaca_stocks
            and self.stock_data_provider == 'capital'
            and self.alpaca_stock_universe
            and 'alpaca' in self.exchanges
        ):
            stock_opps = await self._scan_alpaca_stocks_via_capital(limit=limit // 2)
            opportunities.extend(stock_opps)
        
        # Sort by ocean score
        opportunities.sort(key=lambda x: x.ocean_score, reverse=True)
        
        scan_duration = time.time() - scan_start
        self.last_scan_time = scan_duration
        self.scan_count += 1
        
        # Store top opportunities
        self.hot_opportunities = opportunities[:limit]
        
        # Publish best opportunities
        for opp in self.hot_opportunities[:3]:
           self._publish_opportunity(opp)
        
        print(f"\n🎯 OCEAN SCAN COMPLETE in {scan_duration:.2f}s")
        print(f"   Found {len(opportunities)} opportunities from {self.total_symbols_scanned:,} symbols")
        
        return opportunities[:limit]

    def _publish_opportunity(self, opp: OceanOpportunity) -> None:
        """Publish opportunity to ThoughtBus and ChirpBus."""
        try:
            # 1. ThoughtBus
            if self.thought_bus:
                self.thought_bus.publish(Thought(
                    source="OCEAN_SCANNER",
                    topic="market.opportunity",
                    payload=opp.to_dict()
                ))

            # 2. ChirpBus - use emit_message (ChirpBus doesnt have publish)
            if self.chirp_bus:
                try:
                    self.chirp_bus.emit_message(
                        f"OCEAN:{opp.symbol}:{opp.opportunity_type}:{opp.ocean_score:.2f}",
                        symbol=opp.symbol,
                        confidence=opp.confidence,
                        coherence=opp.ocean_score
                    )
                except Exception as chirp_err:
                    logger.debug(f"ChirpBus emit failed: {chirp_err}")
        except Exception as e:
            logger.error(f"Failed to publish ocean opportunity: {e}")

    def _read_binance_ws_cache(self) -> Optional[Dict[str, Any]]:
        """Read local Binance WS cache if present and fresh."""
        path = self.binance_ws_cache_path
        try:
            if not path or not os.path.exists(path):
                return None
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            generated_at = float(data.get('generated_at', 0) or 0)
            if not generated_at:
                return None
            if (time.time() - generated_at) > self.binance_ws_cache_max_age_s:
                return None
            return data
        except Exception:
            return None

    def _build_alpaca_binance_mapping(self) -> None:
        """Build mapping from Alpaca crypto bases (BTC) to Binance symbols (BTCUSDT)."""
        if self._alpaca_to_binance_map:
            return  # Already built
        # Alpaca crypto universe contains symbols like 'BTC/USD', 'ETH/USD'
        # Binance has pairs like 'BTCUSDT', 'ETHUSDT'
        quote_priority = ['USDT', 'USDC', 'BUSD', 'USD']
        for alpaca_sym in self.alpaca_crypto_universe:
            # Extract base: 'BTC/USD' -> 'BTC'
            base = alpaca_sym.split('/')[0].upper() if '/' in alpaca_sym else alpaca_sym.upper()
            if not base:
                continue
            # Try each quote
            for quote in quote_priority:
                binance_sym = f"{base}{quote}"
                if binance_sym in self.binance_universe:
                    self._alpaca_to_binance_map[base] = binance_sym
                    break
            # Also store without exchange check (we'll verify against cache later)
            if base not in self._alpaca_to_binance_map:
                self._alpaca_to_binance_map[base] = f"{base}USDT"

    async def _scan_alpaca_crypto_via_binance(self, limit: int = 50) -> List[OceanOpportunity]:
        """
        🟡 BINANCE → ALPACA CRYPTO SCANNING
        
        Use FREE Binance WebSocket cache for heavy lifting market scanning.
        Only validate top N candidates via Alpaca API.
        Execute trades on Alpaca.
        """
        opportunities: List[OceanOpportunity] = []
        
        # Build mapping if needed
        self._build_alpaca_binance_mapping()
        
        # 1) Read Binance WS cache (produced by ws_market_data_feeder.py)
        cache = self._read_binance_ws_cache()
        if not cache:
            # Fallback: try direct Binance REST call
            binance = self.exchanges.get('binance')
            if binance and hasattr(binance, 'get_24h_tickers'):
                try:
                    tickers = binance.get_24h_tickers()
                    ticker_cache = {}
                    for t in tickers or []:
                        sym = str(t.get('symbol', '')).upper()
                        if sym:
                            ticker_cache[sym] = {
                                'price': float(t.get('price', t.get('lastPrice', 0)) or 0),
                                'change24h': float(t.get('priceChangePercent', 0) or 0),
                                'volume': float(t.get('volume', t.get('quoteVolume', 0)) or 0),
                                'base': sym[:-4] if sym.endswith('USDT') else sym[:-3] if sym.endswith('USD') else sym,
                                'quote': 'USDT' if sym.endswith('USDT') else 'USD' if sym.endswith('USD') else '',
                                'exchange': 'binance',
                            }
                    cache = {'ticker_cache': ticker_cache, 'prices': {}}
                except Exception:
                    return opportunities
            else:
                return opportunities
        
        ticker_cache = cache.get('ticker_cache', {})
        prices = cache.get('prices', {})
        
        # 2) Find Alpaca-tradeable cryptos in Binance data
        candidates: List[tuple] = []
        for base, binance_sym in self._alpaca_to_binance_map.items():
            # Try multiple keys (with and without 'binance:' prefix)
            ticker = ticker_cache.get(binance_sym) or ticker_cache.get(f"binance:{binance_sym}")
            price = prices.get(base, 0)
            
            if not ticker and not price:
                continue
            
            if not isinstance(ticker, dict):
                continue
            raw_price = ticker.get('price')
            raw_change = ticker.get('change24h')
            raw_volume = ticker.get('volume')
            if raw_price is None or raw_change is None or raw_volume is None:
                continue
            try:
                t_price = float(raw_price)
                t_change = float(raw_change)
                t_volume = float(raw_volume)
            except (TypeError, ValueError):
                continue
            if not all(math.isfinite(value) for value in (t_price, t_change, t_volume)):
                continue
            
            if t_price <= 0:
                continue
            
            candidates.append((base, {
                'price': t_price,
                'change_pct': t_change,
                'volume': t_volume,
                'binance_sym': binance_sym,
            }))
        
        # 3) Sort by absolute 24h change (most active first)
        candidates.sort(key=lambda x: abs(x[1].get('change_pct', 0)), reverse=True)
        
        # 4) Analyze and score
        for base, data in candidates[:max(50, limit * 3)]:
            price = data['price']
            change_pct = data['change_pct']
            volume = data['volume']
            
            # Reconstruct open price from change %
            open_price = price / (1 + (change_pct / 100.0)) if (1 + (change_pct / 100.0)) != 0 else price
            
            ticker_data = {
                'last': price,
                'open': open_price,
                'volume': volume,
                'change_pct': change_pct,
            }
            
            opp = self._analyze_symbol(base, ticker_data, 'alpaca_crypto_via_binance')
            if opp:
                opp.reason = f"Binance scan: {change_pct:+.1f}% | {opp.reason}" if opp.reason else f"Binance scan: {change_pct:+.1f}%"
                opportunities.append(opp)
        
        # 5) Sort by score
        opportunities.sort(key=lambda x: x.ocean_score, reverse=True)
        
        # 6) Validate TOP N via Alpaca API (keeps Alpaca usage minimal)
        if self.alpaca_crypto_validate_top_n > 0:
            to_validate = opportunities[:self.alpaca_crypto_validate_top_n]
            alpaca = self.exchanges.get('alpaca')
            if alpaca:
                for opp in to_validate:
                    try:
                        # Try get_latest_quotes for crypto
                        alpaca_sym = f"{opp.symbol}/USD"
                        if hasattr(alpaca, 'get_latest_quotes'):
                            quotes = alpaca.get_latest_quotes([alpaca_sym])
                            if quotes and alpaca_sym in quotes:
                                q = quotes[alpaca_sym]
                                bid = float(getattr(q, 'bid_price', 0) or 0)
                                ask = float(getattr(q, 'ask_price', 0) or 0)
                                if bid > 0 and ask > 0:
                                    opp.current_price = (bid + ask) / 2
                                    opp.reason = f"{opp.reason} | Alpaca validated"
                        elif hasattr(alpaca, 'get_crypto_quote'):
                            q = alpaca.get_crypto_quote(alpaca_sym) or {}
                            bid = float(q.get('bp', q.get('bid', 0)) or 0)
                            ask = float(q.get('ap', q.get('ask', 0)) or 0)
                            if bid > 0 and ask > 0:
                                opp.current_price = (bid + ask) / 2
                                opp.reason = f"{opp.reason} | Alpaca validated"
                    except Exception:
                        continue
        
        opportunities.sort(key=lambda x: x.ocean_score, reverse=True)
        return opportunities[:limit]

    def _read_capital_stock_cache(self) -> Optional[Dict[str, Any]]:
        """Read local Capital stock cache if present and fresh."""
        path = self.capital_stock_cache_path
        try:
            if not path or not os.path.exists(path):
                return None
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            generated_at = float(data.get('generated_at', 0) or 0)
            if not generated_at:
                return None
            if (time.time() - generated_at) > self.capital_stock_cache_max_age_s:
                return None
            return data
        except Exception:
            return None

    def _ensure_capital_client(self) -> Optional[Any]:
        if self.capital_client is not None:
            return self.capital_client
        if CapitalClient is None:
            self.capital_client = None
            return None
        try:
            client = CapitalClient()
            self.capital_client = client if getattr(client, 'enabled', False) else None
        except Exception:
            self.capital_client = None
        return self.capital_client

    async def _scan_alpaca_stocks_via_capital(self, limit: int = 50) -> List[OceanOpportunity]:
        """Scan a subset of Alpaca-tradeable stocks using Capital.com snapshots."""
        opportunities: List[OceanOpportunity] = []

        # 1) Prefer cache (produced by capital_stock_cache_feeder.py)
        cache = self._read_capital_stock_cache()
        ticker_map = (cache or {}).get('tickers', {}) if isinstance(cache, dict) else {}

        # 2) If no cache, fall back to a lightweight Capital top-list pull.
        if not ticker_map:
            cap = self._ensure_capital_client()
            if not cap:
                return opportunities
            try:
                tickers = cap.get_24h_tickers()
                for t in tickers or []:
                    ticker = (t.get('ticker') or '').strip().upper()
                    if not ticker:
                        continue
                    ticker_map[ticker] = {
                        'price': float(t.get('price', 0) or 0),
                        'bid': float(t.get('bid', 0) or 0),
                        'ask': float(t.get('ask', 0) or 0),
                        'change_pct': float(t.get('priceChangePercent', 0) or 0),
                        'epic': t.get('epic') or t.get('symbol') or '',
                    }
            except Exception:
                return opportunities

        # Only consider symbols that Alpaca says are tradable.
        candidates = []
        for ticker, t in ticker_map.items():
            if ticker in self.alpaca_stock_universe:
                candidates.append((ticker, t))

        # Sort by absolute 24h move (best-effort proxy).
        candidates.sort(key=lambda x: abs(float(x[1].get('change_pct', 0) or 0)), reverse=True)

        # Build pseudo-tickers for analysis.
        tickers_for_analyze: Dict[str, Dict[str, Any]] = {}
        for ticker, t in candidates[: max(10, limit * 5)]:
            price = float(t.get('price', 0) or 0)
            change_pct = float(t.get('change_pct', 0) or 0)
            if price <= 0:
                continue
            # Reconstruct an approximate open from % change (so momentum scoring works).
            open_price = price / (1 + (change_pct / 100.0)) if (1 + (change_pct / 100.0)) != 0 else price
            tickers_for_analyze[ticker] = {
                'last': price,
                'open': open_price,
                'bid': float(t.get('bid', 0) or 0),
                'ask': float(t.get('ask', 0) or 0),
                'change_pct': change_pct,
                'epic': t.get('epic') or '',
            }

        for symbol, ticker in tickers_for_analyze.items():
            try:
                opp = self._analyze_symbol(symbol, ticker, 'alpaca_stocks')
                if opp:
                    opp.reason = (opp.reason + f" | Capital scan") if opp.reason else "Capital scan"
                    opportunities.append(opp)
            except Exception:
                continue

        # Validate only top N with Alpaca quotes (keeps Alpaca usage low).
        opportunities.sort(key=lambda x: x.ocean_score, reverse=True)
        if self.stock_validate_top_n > 0:
            to_validate = opportunities[: self.stock_validate_top_n]
            alpaca = self.exchanges.get('alpaca')
            if alpaca and hasattr(alpaca, 'get_last_quote'):
                for opp in to_validate:
                    try:
                        q = alpaca.get_last_quote(opp.symbol) or {}
                        bid = float(q.get('bp', 0) or 0)
                        ask = float(q.get('ap', 0) or 0)
                        if bid > 0 and ask > 0:
                            opp.current_price = (bid + ask) / 2
                            opp.reason = (opp.reason + " | Alpaca validated") if opp.reason else "Alpaca validated"
                    except Exception:
                        continue

        opportunities.sort(key=lambda x: x.ocean_score, reverse=True)
        return opportunities[:limit]
    
    async def _scan_exchange_universe(
        self, 
        exchange: str, 
        symbols: Set[str],
        limit: int = 50
    ) -> List[OceanOpportunity]:
        """Scan a single exchange's universe for opportunities."""
        opportunities = []
        
        client = self.exchanges.get(exchange)
        if not client:
            return opportunities
        
        # Get batch price data if available
        try:
            if exchange == 'kraken' and hasattr(client, 'get_ticker_batch'):
                tickers = client.get_ticker_batch(list(symbols)[:100])  # Limit API calls
            elif exchange == 'alpaca':
                tickers = await self._get_alpaca_tickers(client, symbols)
            else:
                tickers = {}
        except Exception as e:
            logger.error(f"Ticker fetch error for {exchange}: {e}")
            tickers = {}
        
        for symbol, ticker in tickers.items():
            try:
                opp = self._analyze_symbol(symbol, ticker, exchange)
                if opp and opp.ocean_score > 0.3:  # Minimum score threshold
                    opportunities.append(opp)
            except Exception as e:
                continue
        
        # Sort by score and return top
        opportunities.sort(key=lambda x: x.ocean_score, reverse=True)
        return opportunities[:limit]
    
    def _analyze_symbol(self, symbol: str, ticker: Dict, exchange: str) -> Optional[OceanOpportunity]:
        """Analyze a single symbol and score its opportunity potential."""
        
        price = ticker.get('last', ticker.get('price', ticker.get('c', 0)))
        if not price or price <= 0:
            return None
        
        # Calculate momentum from ticker data
        open_price = ticker.get('open', ticker.get('o', price))
        high = ticker.get('high', ticker.get('h', price))
        low = ticker.get('low', ticker.get('l', price))
        volume = ticker.get('volume', ticker.get('v', 0))
        
        # 24h momentum
        change_pct = ticker.get('priceChangePercent', ticker.get('change_pct', None))
        if change_pct is not None:
            try:
                momentum_24h = float(change_pct)
            except Exception:
                momentum_24h = 0
        elif open_price and open_price > 0:
            momentum_24h = ((price - open_price) / open_price) * 100
        else:
            momentum_24h = 0
        
        # Volatility (high-low range)
        if high and low and low > 0:
            volatility = ((high - low) / low) * 100
        else:
            volatility = 0
        
        # Calculate ocean score
        # Components:
        # - Momentum (higher = better for trend following)
        # - Volume (higher = more liquid)
        # - Volatility (moderate = opportunity without chaos)
        
        # Momentum score (0-0.4) - positive momentum is better
        momentum_score = min(0.4, max(0, momentum_24h / 20))  # 20% = max score
        
        # Volume score (0-0.3); this path remains advisory until a volume-ratio receipt is wired.
        volume_score = 0.15 if volume > 0 else 0
        
        # Volatility score (0-0.3) - sweet spot is 2-10%
        if 2 <= volatility <= 10:
            volatility_score = 0.3
        elif volatility < 2:
            volatility_score = volatility / 2 * 0.3
        else:
            volatility_score = max(0, 0.3 - (volatility - 10) / 50)
        
        ocean_score = momentum_score + volume_score + volatility_score
        
        # Determine opportunity type
        if momentum_24h > 5:
            opp_type = 'momentum'
            reason = f"Strong momentum: {momentum_24h:.1f}% in 24h"
        elif momentum_24h < -5:
            opp_type = 'reversal'
            reason = f"Potential reversal: {momentum_24h:.1f}% down"
        elif volatility > 5:
            opp_type = 'breakout'
            reason = f"High volatility: {volatility:.1f}% range"
        else:
            opp_type = 'stable'
            reason = "Stable with moderate movement"
        
        return OceanOpportunity(
            symbol=symbol,
            exchange=exchange,
            opportunity_type=opp_type,
            current_price=float(price),
            momentum_24h=momentum_24h,
            volume_24h=float(volume) if volume else 0,
            ocean_score=ocean_score,
            confidence=min(1.0, ocean_score / 0.7),  # Normalize to 0-1
            reason=reason,
        )
    
    async def _get_alpaca_tickers(self, client, symbols: Set[str]) -> Dict:
        """Get ticker data for Alpaca symbols."""
        tickers = {}
        
        try:
            # Use get_latest_quotes or similar
            if hasattr(client, 'get_latest_quotes'):
                quotes = client.get_latest_quotes(list(symbols)[:50])
                for symbol, quote in quotes.items():
                    tickers[symbol] = {
                        'last': float(quote.ask_price) if hasattr(quote, 'ask_price') else 0,
                        'bid': float(quote.bid_price) if hasattr(quote, 'bid_price') else 0,
                        'ask': float(quote.ask_price) if hasattr(quote, 'ask_price') else 0,
                    }
        except Exception as e:
            logger.error(f"Alpaca ticker error: {e}")
        
        return tickers
    
    def get_ocean_summary(self) -> Dict:
        """Get a summary of the ocean scanner's state."""
        return {
            'universe_size': {
                'kraken': len(self.kraken_universe),
                'alpaca_crypto': len(self.alpaca_crypto_universe),
                'alpaca_stocks': len(self.alpaca_stock_universe),
                'binance': len(self.binance_universe),
                'total': self.total_symbols_scanned,
            },
            'hot_opportunities': len(self.hot_opportunities),
            'top_5': [opp.to_dict() for opp in self.hot_opportunities[:5]],
            'scan_count': self.scan_count,
            'last_scan_time': self.last_scan_time,
        }
    
    def print_ocean_report(self):
        """Print a beautiful ocean report."""
        print("\n" + "🌊" * 35)
        print("            🐢 OCEAN SCANNER REPORT 🐢")
        print("🌊" * 35)
        
        print(f"\n📊 UNIVERSE SIZE:")
        print(f"   🐙 Kraken:        {len(self.kraken_universe):>6,} pairs")
        print(f"   🦙 Alpaca Crypto: {len(self.alpaca_crypto_universe):>6,} symbols")
        print(f"   📈 Alpaca Stocks: {len(self.alpaca_stock_universe):>6,} symbols")
        print(f"   🟡 Binance:       {len(self.binance_universe):>6,} pairs")
        print(f"   ─────────────────────────")
        print(f"   🌍 TOTAL:         {self.total_symbols_scanned:>6,} opportunities!")
        
        print(f"\n🔥 TOP 10 HOT OPPORTUNITIES:")
        for i, opp in enumerate(self.hot_opportunities[:10], 1):
            emoji = '🚀' if opp.momentum_24h > 5 else '📉' if opp.momentum_24h < -5 else '📊'
            print(f"   {i:>2}. {emoji} {opp.symbol:<12} | {opp.exchange:<8} | "
                  f"Score: {opp.ocean_score:.2f} | Mom: {opp.momentum_24h:>+6.1f}% | {opp.reason[:30]}")
        
        print(f"\n⏱️  Scan #{self.scan_count} completed in {self.last_scan_time:.2f}s")
        print("🌊" * 35)
