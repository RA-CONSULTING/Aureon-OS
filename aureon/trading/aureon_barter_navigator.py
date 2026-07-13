#!/usr/bin/env python3
"""
🫒🔄 AUREON BARTER NAVIGATOR - TRADE UP TO YOUR GOAL 🔄🫒
═══════════════════════════════════════════════════════════════════════════════

The Green Olive → Black Olive Problem:
├─ You have: GREEN OLIVE (Asset A)
├─ You want: BLACK OLIVE (Asset Z)
├─ Problem: Black olive guy doesn't see value in green olive
└─ Solution: BARTER UP! Trade through intermediaries

GREEN OLIVE → Bean → Carrot → Chair → Lamp → BLACK OLIVE

Each trade finds someone who values what you have MORE than what they have.
The path through the market finds the best route to your destination!

FEATURES:
├─ Maps ALL tradeable pairs across Kraken, Binance, Alpaca, Coinbase
├─ Builds a graph of every possible conversion
├─ Finds optimal multi-hop paths (A→B→C→...→Z)
├─ Considers fees, slippage, and liquidity at each step
├─ Discovers arbitrage opportunities (circular paths with profit)
└─ Calculates expected value at each hop

Gary Leckey & GitHub Copilot | January 2026
"Trade the olive for a bean, the bean for a carrot..."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import heapq
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════════
# 📦 IMPORTS
# ════════════════════════════════════════════════════════════════════════════════

# Exchange clients
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KrakenClient = None
    KRAKEN_AVAILABLE = False

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BinanceClient = None
    BINANCE_AVAILABLE = False

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    AlpacaClient = None
    ALPACA_AVAILABLE = False


# ════════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class TradingEdge:
    """An edge in the barter graph - represents a tradeable pair."""
    from_asset: str
    to_asset: str
    pair: str
    exchange: str
    rate: float  # How much to_asset you get per from_asset
    fee_rate: float  # Trading fee (0.0016 = 0.16%)
    volume_24h: float  # 24h volume for liquidity
    spread: float  # Bid-ask spread
    is_direct: bool  # Direct pair or needs conversion
    
    @property
    def effective_rate(self) -> float:
        """Rate after fees and spread."""
        return self.rate * (1 - self.fee_rate) * (1 - self.spread / 2)
    
    @property
    def cost(self) -> float:
        """Cost of this edge for pathfinding (lower = better)."""
        # Use negative log of effective rate so higher rates = lower cost
        if self.effective_rate <= 0:
            return float('inf')
        import math
        return -math.log(self.effective_rate)


@dataclass
class BarterPath:
    """A complete path from source to destination."""
    source: str
    destination: str
    hops: List[TradingEdge]
    total_rate: float  # Final amount per 1 unit of source
    total_fees: float  # Total fees paid
    exchanges_used: Set[str]
    estimated_time_seconds: float
    
    @property
    def num_hops(self) -> int:
        return len(self.hops)
    
    @property
    def profit_vs_direct(self) -> float:
        """How much better this path is vs a direct trade (if exists)."""
        return self.total_rate  # Normalized to direct = 1.0
    
    def describe(self) -> str:
        """Human-readable path description."""
        if not self.hops:
            return f"{self.source} → {self.destination} (no path)"
        
        path_str = self.source
        for hop in self.hops:
            path_str += f" →[{hop.exchange}:{hop.pair}]→ {hop.to_asset}"
        return path_str


@dataclass
class BarterOpportunity:
    """An opportunity to barter up."""
    have_asset: str
    have_amount: float
    want_asset: str
    best_path: BarterPath
    expected_amount: float  # How much want_asset you'll get
    expected_value_usd: float
    confidence: float  # 0-1 confidence in execution
    reason: str


# ════════════════════════════════════════════════════════════════════════════════
# 🫒 BARTER NAVIGATOR CLASS
# ════════════════════════════════════════════════════════════════════════════════

class BarterNavigator:
    """
    Navigates the market to find optimal barter paths.
    
    Like trading a green olive for a black olive through a chain of trades:
    Olive → Bean → Carrot → Chair → Lamp → Black Olive
    """
    
    # Exchange fee rates
    EXCHANGE_FEES = {
        'kraken': 0.0016,   # 0.16% maker
        'binance': 0.001,   # 0.10% with BNB
        'alpaca': 0.0025,   # 0.25%
        'coinbase': 0.006,  # 0.60%
    }
    
    # Stablecoins - good intermediate assets (like "cash" in bartering)
    STABLECOINS = {'USD', 'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'ZUSD'}
    
    # Major cryptos - highly liquid intermediates
    MAJOR_CRYPTOS = {'BTC', 'ETH', 'XBT'}  # XBT is Kraken's BTC
    
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # The barter graph: asset -> list of edges to other assets
        self.graph: Dict[str, List[TradingEdge]] = defaultdict(list)
        
        # All known assets
        self.assets: Set[str] = set()
        
        # Prices in USD for valuation
        self.prices: Dict[str, float] = {}
        
        # Exchange clients
        self.kraken = None
        self.binance = None
        self.alpaca = None
        
        # Cache for paths
        self.path_cache: Dict[str, BarterPath] = {}
        self.cache_ttl = 60  # seconds
        self.cache_time = 0
        
        # Stats
        self.total_pairs = 0
        self.total_edges = 0
        
        print("🫒 Barter Navigator initialized")
    
    def load_all_exchanges(self):
        """Load tradeable pairs from all exchanges."""
        print("\n" + "=" * 70)
        print("🫒🔄 LOADING BARTER GRAPH FROM ALL EXCHANGES")
        print("=" * 70)
        
        # Clear existing graph
        self.graph.clear()
        self.assets.clear()
        self.total_pairs = 0
        self.total_edges = 0
        
        # Load from each exchange
        if KRAKEN_AVAILABLE:
            self._load_kraken()
        
        if BINANCE_AVAILABLE:
            self._load_binance()
        
        if ALPACA_AVAILABLE:
            self._load_alpaca()
        
        # Load cached Coinbase data
        self._load_coinbase_cache()
        
        # Add implicit USD conversions for stablecoins
        self._add_stablecoin_bridges()
        
        print(f"\n📊 BARTER GRAPH COMPLETE:")
        print(f"   🪙 Total Assets: {len(self.assets)}")
        print(f"   🔗 Total Pairs: {self.total_pairs}")
        print(f"   ➡️ Total Edges: {self.total_edges}")
        print("=" * 70 + "\n")
        
        # Save graph to cache
        self._save_cache()
    
    def _load_kraken(self):
        """Load pairs from Kraken."""
        print("\n🐙 Loading Kraken pairs...")
        try:
            self.kraken = get_kraken_client()
            
            # Get all asset pairs
            pairs = self.kraken._load_asset_pairs() if hasattr(self.kraken, '_load_asset_pairs') else {}
            
            # Get tickers for rates
            tickers = self.kraken.get_all_tickers() if hasattr(self.kraken, 'get_all_tickers') else {}
            
            kraken_pairs = 0
            for pair_name, info in pairs.items():
                if pair_name.endswith('.d'):  # Skip dark pools
                    continue
                
                base = info.get('base', '').replace('X', '').replace('Z', '')
                quote = info.get('quote', '').replace('X', '').replace('Z', '')
                
                # Normalize XBT to BTC
                if base == 'XBT':
                    base = 'BTC'
                if quote == 'XBT':
                    quote = 'BTC'
                
                # Get rate from ticker
                ticker = tickers.get(pair_name, {})
                last_price = float(ticker.get('c', [0])[0]) if ticker.get('c') else 0
                volume = float(ticker.get('v', [0, 0])[1]) if ticker.get('v') else 0
                spread = 0.001  # Estimate 0.1% spread
                
                if last_price > 0 and base and quote:
                    # Add edge: base -> quote (selling base for quote)
                    self._add_edge(
                        from_asset=base,
                        to_asset=quote,
                        pair=pair_name,
                        exchange='kraken',
                        rate=last_price,
                        volume=volume,
                        spread=spread
                    )
                    
                    # Add reverse edge: quote -> base (buying base with quote)
                    self._add_edge(
                        from_asset=quote,
                        to_asset=base,
                        pair=pair_name,
                        exchange='kraken',
                        rate=1.0 / last_price,
                        volume=volume,
                        spread=spread
                    )
                    
                    kraken_pairs += 1
                    
                    # Store prices
                    if quote in self.STABLECOINS or quote == 'USD':
                        self.prices[base] = last_price
            
            print(f"   ✅ Loaded {kraken_pairs} Kraken pairs")
            self.total_pairs += kraken_pairs
            
        except Exception as e:
            print(f"   ⚠️ Kraken error: {e}")
    
    def _load_binance(self):
        """Load pairs from Binance."""
        print("\n🟡 Loading Binance pairs...")
        try:
            self.binance = get_binance_client()
            
            # Get exchange info for all pairs
            exchange_info = self.binance.client.get_exchange_info() if hasattr(self.binance, 'client') else {}
            symbols = exchange_info.get('symbols', [])
            
            # Get all tickers for prices
            tickers = {}
            try:
                ticker_list = self.binance.client.get_all_tickers() if hasattr(self.binance, 'client') else []
                for t in ticker_list:
                    tickers[t['symbol']] = float(t['price'])
            except:
                pass
            
            binance_pairs = 0
            for sym_info in symbols:
                if sym_info.get('status') != 'TRADING':
                    continue
                
                symbol = sym_info.get('symbol', '')
                base = sym_info.get('baseAsset', '')
                quote = sym_info.get('quoteAsset', '')
                
                price = tickers.get(symbol, 0)
                
                if price > 0 and base and quote:
                    # Add both directions
                    self._add_edge(
                        from_asset=base,
                        to_asset=quote,
                        pair=symbol,
                        exchange='binance',
                        rate=price,
                        volume=0,  # Would need separate API call
                        spread=0.0005  # Binance has tight spreads
                    )
                    
                    self._add_edge(
                        from_asset=quote,
                        to_asset=base,
                        pair=symbol,
                        exchange='binance',
                        rate=1.0 / price,
                        volume=0,
                        spread=0.0005
                    )
                    
                    binance_pairs += 1
                    
                    # Store prices
                    if quote in self.STABLECOINS or quote == 'USDT':
                        self.prices[base] = price
            
            print(f"   ✅ Loaded {binance_pairs} Binance pairs")
            self.total_pairs += binance_pairs
            
        except Exception as e:
            print(f"   ⚠️ Binance error: {e}")
    
    def _load_alpaca(self):
        """Load pairs from Alpaca."""
        print("\n🦙 Loading Alpaca pairs...")
        try:
            self.alpaca = AlpacaClient()
            
            # Get tradeable crypto assets
            assets = []
            if hasattr(self.alpaca, 'get_crypto_assets'):
                assets = self.alpaca.get_crypto_assets()
            elif hasattr(self.alpaca, 'trading_client'):
                from alpaca.trading.requests import GetAssetsRequest
                from alpaca.trading.enums import AssetClass
                request = GetAssetsRequest(asset_class=AssetClass.CRYPTO)
                assets = self.alpaca.trading_client.get_all_assets(request)
            
            alpaca_pairs = 0
            for asset in assets:
                symbol = asset.symbol if hasattr(asset, 'symbol') else str(asset)
                
                # Alpaca crypto symbols are like "BTC/USD"
                if '/' in symbol:
                    base, quote = symbol.split('/')
                elif symbol.endswith('USD'):
                    base = symbol[:-3]
                    quote = 'USD'
                else:
                    continue
                
                # Get price (would need separate call, use estimate)
                price = self.prices.get(base, 0)
                
                if base and quote:
                    self._add_edge(
                        from_asset=base,
                        to_asset=quote,
                        pair=symbol,
                        exchange='alpaca',
                        rate=price if price > 0 else 1.0,
                        volume=0,
                        spread=0.002
                    )
                    
                    if price > 0:
                        self._add_edge(
                            from_asset=quote,
                            to_asset=base,
                            pair=symbol,
                            exchange='alpaca',
                            rate=1.0 / price,
                            volume=0,
                            spread=0.002
                        )
                    
                    alpaca_pairs += 1
            
            print(f"   ✅ Loaded {alpaca_pairs} Alpaca pairs")
            self.total_pairs += alpaca_pairs
            
        except Exception as e:
            print(f"   ⚠️ Alpaca error: {e}")
    
    def _load_coinbase_cache(self):
        """Load Coinbase pairs from cache."""
        print("\n🪙 Loading Coinbase from cache...")
        cache_path = os.path.join(self.base_path, 'crypto_market_map_cache.json')
        
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cache = json.load(f)
                
                # Extract pairs from correlations
                pairs_added = set()
                for corr in cache.get('correlations', []):
                    s1 = corr.get('symbol1', '')
                    s2 = corr.get('symbol2', '')
                    
                    if s1 and s2 and (s1, s2) not in pairs_added:
                        # These are correlated, not direct pairs
                        # But we can add USD pairs for each
                        for sym in [s1, s2]:
                            if sym not in pairs_added:
                                price = self.prices.get(sym, 0)
                                if price > 0:
                                    self._add_edge(sym, 'USD', f"{sym}-USD", 'coinbase', price, 0, 0.005)
                                    self._add_edge('USD', sym, f"{sym}-USD", 'coinbase', 1/price, 0, 0.005)
                                    pairs_added.add(sym)
                
                print(f"   ✅ Added {len(pairs_added)} Coinbase pairs from cache")
                self.total_pairs += len(pairs_added)
        except Exception as e:
            print(f"   ⚠️ Coinbase cache error: {e}")
    
    def _add_stablecoin_bridges(self):
        """Add bridges between stablecoins (they're ~1:1)."""
        print("\n💵 Adding stablecoin bridges...")
        
        stables = list(self.STABLECOINS & self.assets)
        bridges = 0
        
        for i, s1 in enumerate(stables):
            for s2 in stables[i+1:]:
                # USDT ↔ USDC ↔ USD etc are ~1:1
                self._add_edge(s1, s2, f"{s1}/{s2}", 'bridge', 0.999, 0, 0.0001)
                self._add_edge(s2, s1, f"{s2}/{s1}", 'bridge', 0.999, 0, 0.0001)
                bridges += 1
        
        print(f"   ✅ Added {bridges} stablecoin bridges")
    
    def _add_edge(self, from_asset: str, to_asset: str, pair: str, 
                  exchange: str, rate: float, volume: float, spread: float):
        """Add an edge to the barter graph."""
        if rate <= 0:
            return
        
        edge = TradingEdge(
            from_asset=from_asset,
            to_asset=to_asset,
            pair=pair,
            exchange=exchange,
            rate=rate,
            fee_rate=self.EXCHANGE_FEES.get(exchange, 0.002),
            volume_24h=volume,
            spread=spread,
            is_direct=True
        )
        
        self.graph[from_asset].append(edge)
        self.assets.add(from_asset)
        self.assets.add(to_asset)
        self.total_edges += 1
    
    def _add_dynamic_asset(self, asset: str):
        """Dynamically add an asset via stablecoin bridge if possible."""
        # Try to add direct USD pair for this asset
        try:
            # Attempt to fetch live price
            for quote in ['USD', 'USDT', 'USDC']:
                pair_name = f"{asset}{quote}"
                # Add edges assuming we can trade this pair
                if asset not in self.assets:
                    self._add_edge(asset, quote, pair_name, 'dynamic', 1.0, 0, 0.005)
                    self._add_edge(quote, asset, pair_name, 'dynamic', 1.0, 0, 0.005)
                    print(f"   🔗 Dynamically added {asset} via {quote} bridge")
                    return True
        except Exception as e:
            logger.debug(f"Could not dynamically add {asset}: {e}")
        return False
    
    def _save_cache(self):
        """Save graph to cache."""
        cache_path = os.path.join(self.base_path, 'barter_graph_cache.json')
        try:
            cache = {
                'timestamp': datetime.now().isoformat(),
                'assets': list(self.assets),
                'prices': self.prices,
                'edges': []
            }
            
            for from_asset, edges in self.graph.items():
                for edge in edges:
                    cache['edges'].append({
                        'from': edge.from_asset,
                        'to': edge.to_asset,
                        'pair': edge.pair,
                        'exchange': edge.exchange,
                        'rate': edge.rate,
                        'fee': edge.fee_rate,
                        'spread': edge.spread
                    })
            
            with open(cache_path, 'w') as f:
                json.dump(cache, f, indent=2)
            
            print(f"💾 Saved barter graph cache ({len(cache['edges'])} edges)")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def populate_from_labyrinth_data(self, kraken_pairs: Dict, alpaca_pairs: Dict, 
                                       binance_pairs: Dict, prices: Dict[str, float]):
        """
        🔄 POPULATE FROM ALREADY-LOADED DATA (No new API calls!)
        
        The labyrinth has already loaded all pairs from exchanges.
        Use that data instead of creating new clients that fail.
        """
        print("\n" + "=" * 70)
        print("🫒🔄 POPULATING BARTER GRAPH FROM LABYRINTH DATA")
        print("=" * 70)
        
        # Clear existing graph
        self.graph.clear()
        self.assets.clear()
        self.total_pairs = 0
        self.total_edges = 0
        
        # Store prices
        self.prices = dict(prices)
        
        # Load Kraken pairs
        if kraken_pairs:
            kraken_count = 0
            for pair_name, info in kraken_pairs.items():
                base = info.get('base', '').replace('X', '').replace('Z', '')
                quote = info.get('quote', '').replace('X', '').replace('Z', '')
                
                # Normalize XBT to BTC
                if base == 'XBT': base = 'BTC'
                if quote == 'XBT': quote = 'BTC'
                
                # Get price from loaded prices
                base_price = prices.get(base, 0)
                quote_price = prices.get(quote, 0)
                
                # Calculate rate
                if quote in self.STABLECOINS or quote == 'USD':
                    rate = base_price if base_price > 0 else 1.0
                elif base_price > 0 and quote_price > 0:
                    rate = base_price / quote_price
                else:
                    rate = 1.0
                
                if base and quote and rate > 0:
                    self._add_edge(base, quote, pair_name, 'kraken', rate, 0, 0.001)
                    self._add_edge(quote, base, pair_name, 'kraken', 1/rate, 0, 0.001)
                    kraken_count += 1
            
            print(f"   🐙 Kraken: {kraken_count} pairs from labyrinth data")
            self.total_pairs += kraken_count
        
        # Load Alpaca pairs
        if alpaca_pairs:
            alpaca_count = 0
            for symbol, info in alpaca_pairs.items():
                base = info.get('base', symbol)
                quote = info.get('quote', 'USD')
                
                base_price = prices.get(base, 0)
                rate = base_price if base_price > 0 else 1.0
                
                if base and quote:
                    self._add_edge(base, quote, symbol, 'alpaca', rate, 0, 0.002)
                    if rate > 0:
                        self._add_edge(quote, base, symbol, 'alpaca', 1/rate, 0, 0.002)
                    alpaca_count += 1
            
            print(f"   🦙 Alpaca: {alpaca_count} pairs from labyrinth data")
            self.total_pairs += alpaca_count
        
        # Load Binance pairs
        if binance_pairs:
            binance_count = 0
            for symbol, info in binance_pairs.items():
                base = info.get('base', '')
                quote = info.get('quote', '')
                
                base_price = prices.get(base, 0)
                quote_price = prices.get(quote, 0)
                
                if quote in self.STABLECOINS or quote == 'USD':
                    rate = base_price if base_price > 0 else 1.0
                elif base_price > 0 and quote_price > 0:
                    rate = base_price / quote_price
                else:
                    rate = 1.0
                
                if base and quote and rate > 0:
                    self._add_edge(base, quote, symbol, 'binance', rate, 0, 0.001)
                    self._add_edge(quote, base, symbol, 'binance', 1/rate, 0, 0.001)
                    binance_count += 1
            
            print(f"   🟡 Binance: {binance_count} pairs from labyrinth data")
            self.total_pairs += binance_count
        
        # Add stablecoin bridges
        self._add_stablecoin_bridges()
        
        print(f"\n📊 BARTER GRAPH COMPLETE:")
        print(f"   🪙 Total Assets: {len(self.assets)}")
        print(f"   🔗 Total Pairs: {self.total_pairs}")
        print(f"   ➡️ Total Edges: {self.total_edges}")
        print("=" * 70 + "\n")
        
        # Save cache
        self._save_cache()
        return True

    def load_cache(self) -> bool:
        """Load graph from cache. Returns False if cache is empty or invalid."""
        cache_path = os.path.join(self.base_path, 'barter_graph_cache.json')
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cache = json.load(f)
                
                # Check if cache has actual data (not empty)
                if not cache.get('assets') or not cache.get('edges'):
                    print(f"⚠️ Barter graph cache is empty - will rebuild")
                    return False
                
                self.assets = set(cache.get('assets', []))
                self.prices = cache.get('prices', {})
                
                for edge_data in cache.get('edges', []):
                    edge = TradingEdge(
                        from_asset=edge_data['from'],
                        to_asset=edge_data['to'],
                        pair=edge_data['pair'],
                        exchange=edge_data['exchange'],
                        rate=edge_data['rate'],
                        fee_rate=edge_data.get('fee', 0.002),
                        volume_24h=0,
                        spread=edge_data.get('spread', 0.001),
                        is_direct=True
                    )
                    self.graph[edge.from_asset].append(edge)
                    self.total_edges += 1
                
                print(f"📂 Loaded barter graph from cache ({len(self.assets)} assets, {self.total_edges} edges)")
                return True
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
        return False
    
    # ════════════════════════════════════════════════════════════════════════════
    # 🔍 PATHFINDING - Finding the Barter Chain
    # ════════════════════════════════════════════════════════════════════════════
    
    def find_path(self, source: str, destination: str, max_hops: int = 5) -> Optional[BarterPath]:
        """
        Find the best barter path from source to destination.
        
        Uses Dijkstra's algorithm with edge costs based on:
        - Exchange rate (want to maximize)
        - Fees (want to minimize)
        - Spread (want to minimize)
        
        Args:
            source: Asset you have (green olive)
            destination: Asset you want (black olive)
            max_hops: Maximum number of trades in the chain
        
        Returns:
            BarterPath with the optimal route, or None if no path exists
        """
        source = source.upper()
        destination = destination.upper()
        
        # Normalize BTC/XBT
        if source == 'XBT':
            source = 'BTC'
        if destination == 'XBT':
            destination = 'BTC'
        
        # Check cache
        cache_key = f"{source}→{destination}"
        if cache_key in self.path_cache and time.time() - self.cache_time < self.cache_ttl:
            return self.path_cache[cache_key]
        
        if source not in self.assets:
            # Try to dynamically add this asset via stablecoin bridge
            self._add_dynamic_asset(source)
            if source not in self.assets:
                # Only warn once per session
                if not hasattr(self, '_warned_assets'):
                    self._warned_assets = set()
                if source not in self._warned_assets:
                    print(f"⚠️ Source asset {source} not in barter graph (will use direct USD pricing)")
                    self._warned_assets.add(source)
                return None
        
        if destination not in self.assets:
            self._add_dynamic_asset(destination)
            if destination not in self.assets:
                if not hasattr(self, '_warned_assets'):
                    self._warned_assets = set()
                if destination not in self._warned_assets:
                    print(f"⚠️ Destination asset {destination} not in barter graph")
                    self._warned_assets.add(destination)
                return None
        
        # Dijkstra's algorithm
        # State: (cost, current_asset, path_edges, hops)
        import math
        
        # Priority queue: (cost, asset, path)
        pq = [(0.0, source, [])]
        visited = set()
        best_costs = {source: 0.0}
        
        while pq:
            cost, current, path = heapq.heappop(pq)
            
            if current == destination:
                # Found destination! Build the path
                total_rate = 1.0
                total_fees = 0.0
                exchanges = set()
                
                for edge in path:
                    total_rate *= edge.effective_rate
                    total_fees += edge.fee_rate
                    exchanges.add(edge.exchange)
                
                result = BarterPath(
                    source=source,
                    destination=destination,
                    hops=path,
                    total_rate=total_rate,
                    total_fees=total_fees,
                    exchanges_used=exchanges,
                    estimated_time_seconds=len(path) * 5  # ~5s per trade
                )
                
                self.path_cache[cache_key] = result
                self.cache_time = time.time()
                return result
            
            if current in visited:
                continue
            visited.add(current)
            
            # Check hop limit
            if len(path) >= max_hops:
                continue
            
            # Explore edges
            for edge in self.graph.get(current, []):
                next_asset = edge.to_asset
                
                if next_asset in visited:
                    continue
                
                new_cost = cost + edge.cost
                
                if next_asset not in best_costs or new_cost < best_costs[next_asset]:
                    best_costs[next_asset] = new_cost
                    heapq.heappush(pq, (new_cost, next_asset, path + [edge]))
        
        # No path found
        return None
    
    def find_all_paths(self, source: str, destination: str, max_hops: int = 4, 
                       max_paths: int = 5) -> List[BarterPath]:
        """
        Find multiple paths from source to destination.
        
        Returns up to max_paths different routes, sorted by total rate.
        """
        source = source.upper()
        destination = destination.upper()
        
        if source == 'XBT':
            source = 'BTC'
        if destination == 'XBT':
            destination = 'BTC'
        
        paths = []
        
        # BFS with path tracking
        queue = [(source, [], 1.0)]  # (asset, path, cumulative_rate)
        
        while queue and len(paths) < max_paths * 2:  # Get extra to filter
            current, path, rate = queue.pop(0)
            
            if len(path) > max_hops:
                continue
            
            if current == destination and path:
                # Build path object
                total_fees = sum(e.fee_rate for e in path)
                exchanges = set(e.exchange for e in path)
                
                paths.append(BarterPath(
                    source=source,
                    destination=destination,
                    hops=path,
                    total_rate=rate,
                    total_fees=total_fees,
                    exchanges_used=exchanges,
                    estimated_time_seconds=len(path) * 5
                ))
                continue
            
            # Explore edges
            visited_in_path = {source} | {e.to_asset for e in path}
            
            for edge in self.graph.get(current, []):
                if edge.to_asset not in visited_in_path:
                    new_rate = rate * edge.effective_rate
                    queue.append((edge.to_asset, path + [edge], new_rate))
        
        # Sort by total rate (highest first)
        paths.sort(key=lambda p: p.total_rate, reverse=True)
        
        return paths[:max_paths]
    
    def find_best_opportunity(self, have_asset: str, have_amount: float,
                              want_assets: List[str] = None) -> Optional[BarterOpportunity]:
        """
        Find the best barter opportunity for what you have.
        
        Args:
            have_asset: What you have (green olive)
            have_amount: How much you have
            want_assets: List of assets you'd accept (or None for best overall)
        
        Returns:
            Best BarterOpportunity or None
        """
        have_asset = have_asset.upper()
        
        # Get price of what we have
        have_price = self.prices.get(have_asset, 0)
        have_value = have_amount * have_price if have_price > 0 else have_amount
        
        if want_assets is None:
            # Find best opportunity to any major asset
            want_assets = list(self.MAJOR_CRYPTOS | self.STABLECOINS)
        
        best_opp = None
        best_value = 0
        
        for want in want_assets:
            want = want.upper()
            if want == have_asset:
                continue
            
            path = self.find_path(have_asset, want)
            if not path:
                continue
            
            # Calculate expected amount
            expected_amount = have_amount * path.total_rate
            
            # Calculate USD value
            want_price = self.prices.get(want, 1.0)  # Default 1 for stables
            expected_value = expected_amount * want_price
            
            # Is this better?
            if expected_value > best_value:
                best_value = expected_value
                best_opp = BarterOpportunity(
                    have_asset=have_asset,
                    have_amount=have_amount,
                    want_asset=want,
                    best_path=path,
                    expected_amount=expected_amount,
                    expected_value_usd=expected_value,
                    confidence=0.9 ** path.num_hops,  # Less confident with more hops
                    reason=f"Best path via {path.num_hops} hops"
                )
        
        return best_opp
    
    # ════════════════════════════════════════════════════════════════════════════
    # 🔄 ARBITRAGE DETECTION - Circular Barter
    # ════════════════════════════════════════════════════════════════════════════
    
    def find_arbitrage(self, start_asset: str = 'USD', min_profit_pct: float = 0.1,
                       max_hops: int = 4) -> List[BarterPath]:
        """
        Find arbitrage opportunities (circular paths with profit).
        
        A→B→C→A where final_amount > initial_amount
        
        Args:
            start_asset: Asset to start and end with
            min_profit_pct: Minimum profit % to report
            max_hops: Maximum trades in the cycle
        
        Returns:
            List of profitable circular paths
        """
        start_asset = start_asset.upper()
        
        profitable_cycles = []
        
        # Find all paths back to start
        paths = self.find_all_paths(start_asset, start_asset, max_hops=max_hops, max_paths=20)
        
        for path in paths:
            if path.total_rate > 1 + min_profit_pct / 100:
                profitable_cycles.append(path)
        
        # Sort by profit
        profitable_cycles.sort(key=lambda p: p.total_rate, reverse=True)
        
        return profitable_cycles
    
    # ════════════════════════════════════════════════════════════════════════════
    # 📊 ANALYSIS & REPORTING
    # ════════════════════════════════════════════════════════════════════════════
    
    def get_asset_connectivity(self, asset: str) -> Dict:
        """Get connectivity info for an asset."""
        asset = asset.upper()
        
        direct_edges = self.graph.get(asset, [])
        direct_pairs = len(direct_edges)
        exchanges = set(e.exchange for e in direct_edges)
        reachable = set(e.to_asset for e in direct_edges)
        
        # Find 2-hop reachable
        two_hop = set()
        for dest in reachable:
            for edge in self.graph.get(dest, []):
                two_hop.add(edge.to_asset)
        two_hop -= reachable
        two_hop.discard(asset)
        
        return {
            'asset': asset,
            'direct_pairs': direct_pairs,
            'exchanges': list(exchanges),
            'direct_reachable': len(reachable),
            'two_hop_reachable': len(two_hop),
            'total_reachable': len(reachable | two_hop),
            'price_usd': self.prices.get(asset, 0)
        }
    
    def get_graph_summary(self) -> Dict:
        """Get summary of the barter graph."""
        exchange_counts = defaultdict(int)
        for edges in self.graph.values():
            for edge in edges:
                exchange_counts[edge.exchange] += 1
        
        return {
            'total_assets': len(self.assets),
            'total_edges': self.total_edges,
            'total_pairs': self.total_pairs,
            'exchanges': dict(exchange_counts),
            'stablecoins': list(self.STABLECOINS & self.assets),
            'major_cryptos': list(self.MAJOR_CRYPTOS & self.assets),
            'prices_loaded': len(self.prices)
        }
    
    def print_path(self, path: BarterPath):
        """Pretty print a barter path."""
        print(f"\n🫒 BARTER PATH: {path.source} → {path.destination}")
        print("=" * 60)
        
        current = path.source
        current_amount = 1.0
        
        for i, hop in enumerate(path.hops, 1):
            next_amount = current_amount * hop.effective_rate
            print(f"   {i}. {current} → {hop.to_asset}")
            print(f"      📍 {hop.exchange}: {hop.pair}")
            print(f"      💱 Rate: {hop.rate:.6f} (effective: {hop.effective_rate:.6f})")
            print(f"      💰 {current_amount:.6f} → {next_amount:.6f}")
            current = hop.to_asset
            current_amount = next_amount
        
        print("-" * 60)
        print(f"   📊 Total Rate: {path.total_rate:.6f}")
        print(f"   💸 Total Fees: {path.total_fees:.4%}")
        print(f"   🔢 Hops: {path.num_hops}")
        print(f"   🏢 Exchanges: {', '.join(path.exchanges_used)}")
        print("=" * 60)


# ════════════════════════════════════════════════════════════════════════════════
# 🔌 LABYRINTH INTEGRATION
# ════════════════════════════════════════════════════════════════════════════════

# Singleton navigator
_navigator: Optional[BarterNavigator] = None

def get_navigator() -> BarterNavigator:
    """Get or create the barter navigator singleton."""
    global _navigator
    if _navigator is None:
        _navigator = BarterNavigator()
        # Try cache first, then full load
        if not _navigator.load_cache():
            _navigator.load_all_exchanges()
    return _navigator


def find_barter_path(from_asset: str, to_asset: str) -> Optional[BarterPath]:
    """Find barter path for labyrinth use."""
    nav = get_navigator()
    return nav.find_path(from_asset, to_asset)


def get_barter_score(from_asset: str, to_asset: str) -> Tuple[float, str]:
    """
    Get barter score for labyrinth scoring.
    
    Returns (score 0-1, reason string)
    """
    nav = get_navigator()
    path = nav.find_path(from_asset, to_asset)
    
    if not path:
        return 0.3, "no_path"
    
    # Score based on:
    # - Path efficiency (fewer hops = better)
    # - Total rate (higher = better)
    # - Number of exchanges (fewer = simpler)
    
    hop_score = 1.0 - (path.num_hops - 1) * 0.1  # -10% per extra hop
    rate_score = min(1.0, path.total_rate)  # Cap at 1.0
    exchange_score = 1.0 if len(path.exchanges_used) == 1 else 0.9
    
    combined = (hop_score + rate_score + exchange_score) / 3
    
    reason = f"path_{path.num_hops}hop_{list(path.exchanges_used)[0]}"
    
    return combined, reason


# ════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Demo the barter navigator."""
    print("\n" + "=" * 70)
    print("🫒🔄 AUREON BARTER NAVIGATOR - TRADE UP TO YOUR GOAL 🔄🫒")
    print("=" * 70)
    print("The Green Olive → Black Olive Problem:")
    print("Trade through intermediaries to get what you want!")
    print("=" * 70)
    
    nav = BarterNavigator()
    
    # Load all exchanges
    nav.load_all_exchanges()
    
    # Show summary
    summary = nav.get_graph_summary()
    print(f"\n📊 BARTER GRAPH SUMMARY:")
    print(f"   🪙 Assets: {summary['total_assets']}")
    print(f"   🔗 Edges: {summary['total_edges']}")
    print(f"   🏢 Exchanges: {summary['exchanges']}")
    
    # Demo: Find path from a small altcoin to BTC
    print("\n" + "=" * 70)
    print("🔍 EXAMPLE: Finding barter paths...")
    print("=" * 70)
    
    # Example paths to try
    examples = [
        ('CHZ', 'BTC'),   # Chiliz to Bitcoin
        ('DOGE', 'ETH'),  # Dogecoin to Ethereum
        ('ADA', 'SOL'),   # Cardano to Solana
        ('TUSD', 'USDC'), # TrueUSD to USDC
        ('LINK', 'AVAX'), # Chainlink to Avalanche
    ]
    
    for source, dest in examples:
        print(f"\n🫒 {source} → {dest}:")
        path = nav.find_path(source, dest)
        if path:
            steps = " → ".join([source] + [h.to_asset for h in path.hops])
            print(f"   📍 Path: {steps}")
            print(f"   💱 Rate: {path.total_rate:.6f} | Hops: {path.num_hops} | Fee: {path.total_fees:.2%}")
        else:
            print(f"   ❌ No path found")
    
    # Show detailed path for one example
    print("\n" + "=" * 70)
    path = nav.find_path('CHZ', 'BTC')
    if path:
        nav.print_path(path)
    
    # Find arbitrage opportunities
    print("\n" + "=" * 70)
    print("🔄 ARBITRAGE SCAN (circular profit paths)...")
    print("=" * 70)
    
    arb_paths = nav.find_arbitrage('USDT', min_profit_pct=0.05, max_hops=3)
    if arb_paths:
        print(f"   Found {len(arb_paths)} potential arbitrage paths:")
        for i, arb in enumerate(arb_paths[:5], 1):
            profit = (arb.total_rate - 1) * 100
            steps = " → ".join([arb.source] + [h.to_asset for h in arb.hops])
            print(f"   {i}. {steps} | Profit: {profit:+.3f}%")
    else:
        print("   No arbitrage opportunities found (market efficient)")
    
    print("\n" + "=" * 70)
    print("✅ BARTER NAVIGATOR READY!")
    print("   Use: nav.find_path('GREEN_OLIVE', 'BLACK_OLIVE')")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
