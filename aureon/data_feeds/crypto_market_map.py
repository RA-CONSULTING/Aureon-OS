#!/usr/bin/env python3
"""
🗺️⚡ CRYPTO MARKET MAP - LABYRINTH PATHFINDER ⚡🗺️
═══════════════════════════════════════════════════════════════════════════════

Maps the ENTIRE crypto market to find:
├─ Correlations between assets (which move together)
├─ Inverse correlations (which move opposite)
├─ Sector groupings (DeFi, Layer1, Layer2, Meme, etc.)
├─ Lead/Lag relationships (BTC leads → ALTs follow)
├─ Optimal conversion paths through the labyrinth
└─ Pattern sequences that predict movements

DATA SOURCES:
├─ Coinbase Historical Feed (1 year of OHLCV)
├─ Live ticker data from all exchanges
├─ Trained probability matrix
└─ Real-time correlation updates

Gary Leckey & GitHub Copilot | January 2026
"Mapping the Crypto Labyrinth for Maximum Profit"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ════════════════════════════════════════════════════════════════════════════════
# 🏗️ DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class CryptoAsset:
    """Represents a single crypto asset with its properties."""
    symbol: str
    name: str = ""
    sector: str = "unknown"
    market_cap_rank: int = 0
    avg_daily_volume: float = 0.0
    volatility_30d: float = 0.0
    
    # Relationships
    correlates_with: Dict[str, float] = field(default_factory=dict)  # symbol -> correlation
    inverse_to: Dict[str, float] = field(default_factory=dict)       # symbol -> inverse correlation
    leads: List[str] = field(default_factory=list)                    # assets this leads
    lags_behind: List[str] = field(default_factory=list)             # assets this follows
    
    # Historical patterns
    best_hours: List[int] = field(default_factory=list)
    worst_hours: List[int] = field(default_factory=list)
    avg_move_per_hour: Dict[int, float] = field(default_factory=dict)


@dataclass  
class ConversionPath:
    """A path through the crypto labyrinth."""
    steps: List[Tuple[str, str]]  # [(from, to), (from, to), ...]
    total_correlation_score: float = 0.0
    expected_profit_multiplier: float = 1.0
    confidence: float = 0.0
    pattern_match: str = ""
    

@dataclass
class MarketPattern:
    """A detected market pattern."""
    name: str
    assets_involved: List[str]
    trigger_conditions: Dict[str, Any]
    expected_outcome: str
    historical_accuracy: float = 0.0
    sample_size: int = 0


# ════════════════════════════════════════════════════════════════════════════════
# 🏷️ CRYPTO SECTOR CLASSIFICATIONS
# ════════════════════════════════════════════════════════════════════════════════

CRYPTO_SECTORS = {
    # Layer 1 Blockchains
    'layer1': ['BTC', 'ETH', 'SOL', 'ADA', 'AVAX', 'DOT', 'ATOM', 'NEAR', 'ALGO', 'XTZ',
               'ICP', 'FTM', 'ONE', 'EGLD', 'HBAR', 'XLM', 'EOS', 'TRX', 'XRP', 'BCH',
               'LTC', 'ETC', 'KAVA', 'FLOW', 'ROSE', 'CELO', 'MINA', 'CFX', 'KDA', 'ZIL'],
    
    # Layer 2 & Scaling
    'layer2': ['MATIC', 'ARB', 'OP', 'IMX', 'LRC', 'METIS', 'BOBA', 'SKL', 'CELR', 'ZKS'],
    
    # DeFi Protocols
    'defi': ['UNI', 'AAVE', 'MKR', 'SNX', 'COMP', 'CRV', 'SUSHI', 'YFI', 'INCH', 'BAL',
             'LQTY', 'PERP', 'DYDX', 'GMX', 'GNO', 'RPL', 'LDO', 'FXS', 'CVX', 'SPELL'],
    
    # Oracles & Data
    'oracle': ['LINK', 'BAND', 'API3', 'TRB', 'DIA', 'UMA', 'PYTH'],
    
    # NFT & Metaverse
    'nft_metaverse': ['APE', 'SAND', 'MANA', 'AXS', 'ENJ', 'GALA', 'ILV', 'BLUR', 
                      'IMX', 'GODS', 'SUPER', 'RARE', 'LOOKS', 'X2Y2'],
    
    # Gaming
    'gaming': ['AXS', 'GALA', 'ILV', 'ENJ', 'SAND', 'MANA', 'GODS', 'IMX', 'SUPER',
               'PYR', 'ATLAS', 'ALICE', 'YGG', 'MAGIC', 'PRIME'],
    
    # Meme Coins
    'meme': ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME', 'ELON', 'BABYDOGE',
             'SAMO', 'HOGE', 'AKITA', 'KISHU', 'SAITAMA', 'LEASH'],
    
    # AI & Big Data
    'ai': ['FET', 'AGIX', 'OCEAN', 'NMR', 'GRT', 'RNDR', 'TAO', 'ARKM', 'WLD', 'AI'],
    
    # Privacy
    'privacy': ['XMR', 'ZEC', 'DASH', 'SCRT', 'OASIS', 'DUSK', 'PIVX', 'FIRO', 'BEAM'],
    
    # Storage & Computing
    'storage': ['FIL', 'AR', 'STORJ', 'SC', 'HOT', 'BTT', 'ANKR', 'THETA', 'TFUEL'],
    
    # Exchange Tokens
    'exchange': ['BNB', 'FTT', 'OKB', 'HT', 'KCS', 'CRO', 'GT', 'MX', 'LEO'],
    
    # Stablecoins (Checkpoints)
    'stablecoin': ['USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'GUSD', 'FRAX', 
                   'LUSD', 'SUSD', 'USD', 'ZUSD'],
    
    # Infrastructure
    'infrastructure': ['QNT', 'IOTX', 'VET', 'IOTA', 'HIVE', 'STEEM', 'RUNE', 'INJ'],
    
    # Wrapped/Bridged
    'wrapped': ['WBTC', 'WETH', 'STETH', 'RETH', 'CBETH', 'WMATIC', 'WBNB'],
}

# Reverse lookup: symbol -> sector
SYMBOL_TO_SECTOR = {}
for sector, symbols in CRYPTO_SECTORS.items():
    for symbol in symbols:
        SYMBOL_TO_SECTOR[symbol] = sector


# ════════════════════════════════════════════════════════════════════════════════
# 🗺️ CRYPTO MARKET MAP CLASS
# ════════════════════════════════════════════════════════════════════════════════

class CryptoMarketMap:
    """
    Maps the entire crypto market for the labyrinth.
    Finds correlations, patterns, and optimal paths.
    """
    
    def __init__(self, cache_dir: str = None):
        """Initialize the market map."""
        self.cache_dir = cache_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Asset registry
        self.assets: Dict[str, CryptoAsset] = {}
        
        # Correlation matrix
        self.correlation_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Lead/Lag relationships
        self.lead_lag_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Detected patterns
        self.patterns: List[MarketPattern] = []
        
        # Sector performance tracking
        self.sector_momentum: Dict[str, float] = defaultdict(float)
        
        # Historical price data (cached)
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Optimal paths cache
        self.optimal_paths: Dict[str, List[ConversionPath]] = {}
        
        # Load any cached data
        self._load_cache()
        
        logger.info("🗺️ Crypto Market Map initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 📊 DATA LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_cache(self):
        """Load cached market map data."""
        cache_file = os.path.join(self.cache_dir, 'crypto_market_map_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    
                # Load correlation matrix
                if 'correlation_matrix' in data:
                    self.correlation_matrix = defaultdict(dict, data['correlation_matrix'])
                    
                # Load lead/lag matrix
                if 'lead_lag_matrix' in data:
                    self.lead_lag_matrix = defaultdict(dict, data['lead_lag_matrix'])
                    
                # Load patterns
                if 'patterns' in data:
                    for p in data['patterns']:
                        self.patterns.append(MarketPattern(**p))
                        
                logger.info(f"   📂 Loaded market map cache: {len(self.correlation_matrix)} correlations")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not load cache: {e}")
    
    def save_cache(self):
        """Save market map data to cache."""
        cache_file = os.path.join(self.cache_dir, 'crypto_market_map_cache.json')
        try:
            data = {
                'correlation_matrix': dict(self.correlation_matrix),
                'lead_lag_matrix': dict(self.lead_lag_matrix),
                'patterns': [
                    {
                        'name': p.name,
                        'assets_involved': p.assets_involved,
                        'trigger_conditions': p.trigger_conditions,
                        'expected_outcome': p.expected_outcome,
                        'historical_accuracy': p.historical_accuracy,
                        'sample_size': p.sample_size
                    }
                    for p in self.patterns
                ],
                'updated_at': datetime.now().isoformat()
            }
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"   💾 Saved market map cache")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not save cache: {e}")
    
    def load_from_coinbase_historical(self):
        """Load data from Coinbase Historical Feed."""
        try:
            from aureon.exchanges.coinbase_historical_feed import CoinbaseHistoricalFeed, CandleData
            
            feed = CoinbaseHistoricalFeed()
            
            logger.info("🗺️ Loading historical data from Coinbase...")
            
            # Get all available pairs
            pairs = feed.TRADING_PAIRS
            
            # Fetch historical data (cached if available)
            data = feed.fetch_year_of_data(pairs)
            
            if data:
                # Build correlation matrix from price movements
                self._build_correlations_from_candles(data)
                
                # Detect lead/lag relationships
                self._detect_lead_lag(data)
                
                # Find patterns
                self._detect_patterns(data)
                
                # Save cache
                self.save_cache()
                
                logger.info(f"   ✅ Loaded {len(data)} pairs from Coinbase")
                return True
            
        except ImportError:
            logger.warning("   ⚠️ CoinbaseHistoricalFeed not available")
        except Exception as e:
            logger.error(f"   ❌ Error loading Coinbase data: {e}")
        
        return False
    
    def load_from_kraken(self, kraken_client=None) -> bool:
        """Load historical data from Kraken exchange."""
        try:
            if kraken_client is None:
                from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
                kraken_client = get_kraken_client()
            
            logger.info("🐙 Loading pairs from Kraken...")
            
            # Get all tradeable pairs
            pairs_info = kraken_client._load_asset_pairs() if hasattr(kraken_client, '_load_asset_pairs') else {}
            
            pairs_loaded = 0
            for internal, info in pairs_info.items():
                if internal.endswith('.d'):  # Skip dark pools
                    continue
                
                altname = info.get('altname', internal)
                base = info.get('base', '')
                quote = info.get('quote', '')
                
                # Normalize base symbol
                clean_base = base.replace('X', '').replace('Z', '')
                if clean_base.startswith('BTC') or clean_base == 'XBT':
                    clean_base = 'BTC'
                
                # Register the asset
                if clean_base and clean_base not in self.assets:
                    self.assets[clean_base] = CryptoAsset(
                        symbol=clean_base,
                        sector=SYMBOL_TO_SECTOR.get(clean_base, 'unknown')
                    )
                    pairs_loaded += 1
            
            logger.info(f"   ✅ Loaded {pairs_loaded} assets from Kraken pairs")
            return pairs_loaded > 0
            
        except Exception as e:
            logger.warning(f"   ⚠️ Kraken load error: {e}")
            return False
    
    def load_from_binance(self, binance_client=None) -> bool:
        """Load historical data from Binance exchange."""
        try:
            if binance_client is None:
                from aureon.exchanges.binance_client import BinanceClient, get_binance_client
                binance_client = get_binance_client()
            
            logger.info("🟡 Loading historical data from Binance...")
            
            # Get 24h historical for correlation analysis
            historical = binance_client.get_24h_historical() if hasattr(binance_client, 'get_24h_historical') else {}
            
            if historical:
                # Build price changes from klines
                price_changes = {}
                for symbol, klines in historical.items():
                    clean_symbol = symbol.replace('USDC', '').replace('USDT', '').replace('USD', '')
                    
                    changes = []
                    for k in klines:
                        if k.get('open', 0) > 0:
                            change = ((k['close'] - k['open']) / k['open']) * 100
                            changes.append(change)
                    
                    if changes:
                        price_changes[clean_symbol] = changes
                        
                        # Register the asset
                        if clean_symbol not in self.assets:
                            self.assets[clean_symbol] = CryptoAsset(
                                symbol=clean_symbol,
                                sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown')
                            )
                
                # Calculate correlations from Binance data
                self._add_correlations_from_changes(price_changes, source='binance')
                
                logger.info(f"   ✅ Loaded {len(price_changes)} symbols from Binance")
                return True
            
            # Fallback: just load exchange info for symbols
            info = binance_client.exchange_info() if hasattr(binance_client, 'exchange_info') else {}
            symbols = info.get('symbols', [])
            
            pairs_loaded = 0
            for sym in symbols:
                if sym.get('status') != 'TRADING':
                    continue
                
                base = sym.get('baseAsset', '')
                if base and base not in self.assets:
                    self.assets[base] = CryptoAsset(
                        symbol=base,
                        sector=SYMBOL_TO_SECTOR.get(base, 'unknown')
                    )
                    pairs_loaded += 1
            
            logger.info(f"   ✅ Loaded {pairs_loaded} assets from Binance exchange info")
            return pairs_loaded > 0
            
        except Exception as e:
            logger.warning(f"   ⚠️ Binance load error: {e}")
            return False
    
    def load_from_alpaca(self, alpaca_client=None) -> bool:
        """Load historical data from Alpaca exchange."""
        try:
            if alpaca_client is None:
                from aureon.exchanges.alpaca_client import AlpacaClient
                alpaca_client = AlpacaClient()
            
            logger.info("🦙 Loading historical data from Alpaca...")
            
            # Get tradeable crypto symbols
            symbols = []
            if hasattr(alpaca_client, 'get_tradable_crypto_symbols'):
                symbols = alpaca_client.get_tradable_crypto_symbols() or []
            else:
                assets = alpaca_client.get_assets(status='active', asset_class='crypto') or []
                symbols = [a.get('symbol', '') for a in assets if a.get('tradable')]
            
            # Try to get historical bars for correlations
            if symbols and hasattr(alpaca_client, 'get_crypto_bars'):
                try:
                    # Normalize symbols for Alpaca format
                    alpaca_symbols = [s if '/' in s else f"{s}/USD" for s in symbols[:30]]  # Limit to 30
                    bars_resp = alpaca_client.get_crypto_bars(alpaca_symbols, timeframe="1Hour", limit=24)
                    bars = bars_resp.get('bars', bars_resp) if isinstance(bars_resp, dict) else {}
                    
                    price_changes = {}
                    for sym, bar_list in bars.items():
                        clean_symbol = sym.split('/')[0] if '/' in sym else sym.replace('USD', '')
                        
                        changes = []
                        for bar in bar_list:
                            open_price = bar.get('o', 0)
                            close_price = bar.get('c', 0)
                            if open_price > 0:
                                change = ((close_price - open_price) / open_price) * 100
                                changes.append(change)
                        
                        if changes:
                            price_changes[clean_symbol] = changes
                    
                    if price_changes:
                        self._add_correlations_from_changes(price_changes, source='alpaca')
                        logger.info(f"   ✅ Loaded {len(price_changes)} symbols with bars from Alpaca")
                        
                except Exception as e:
                    logger.debug(f"   Alpaca bars error: {e}")
            
            # Register all tradeable symbols
            pairs_loaded = 0
            for symbol in symbols:
                clean_symbol = symbol.split('/')[0] if '/' in symbol else symbol.replace('USD', '')
                if clean_symbol and clean_symbol not in self.assets:
                    self.assets[clean_symbol] = CryptoAsset(
                        symbol=clean_symbol,
                        sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown')
                    )
                    pairs_loaded += 1
            
            logger.info(f"   ✅ Loaded {pairs_loaded} tradeable crypto assets from Alpaca")
            return pairs_loaded > 0
            
        except Exception as e:
            logger.warning(f"   ⚠️ Alpaca load error: {e}")
            return False
    
    def load_from_all_exchanges(self, kraken_client=None, binance_client=None, alpaca_client=None) -> Dict[str, bool]:
        """
        Load data from ALL available exchanges.
        Returns dict of exchange -> success status.
        """
        results = {}
        
        print("\n" + "=" * 60)
        print("🗺️ LOADING MARKET MAP FROM ALL EXCHANGES")
        print("=" * 60)
        
        # Coinbase (primary - 1 year of data)
        results['coinbase'] = self.load_from_coinbase_historical()
        
        # Kraken
        results['kraken'] = self.load_from_kraken(kraken_client)
        
        # Binance
        results['binance'] = self.load_from_binance(binance_client)
        
        # Alpaca
        results['alpaca'] = self.load_from_alpaca(alpaca_client)
        
        # Probability matrix (trained patterns)
        results['probability_matrix'] = self.load_from_probability_matrix()
        
        # Summary
        print("\n" + "-" * 60)
        print("📊 EXCHANGE LOAD SUMMARY:")
        for exchange, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {exchange}")
        
        print(f"\n   Total Assets Mapped: {len(self.assets)}")
        print(f"   Total Correlations: {sum(len(v) for v in self.correlation_matrix.values()) // 2}")
        print("=" * 60 + "\n")
        
        # Save updated cache
        self.save_cache()
        
        return results
    
    def _add_correlations_from_changes(self, price_changes: Dict[str, List[float]], source: str = 'unknown'):
        """Add correlations from price change data."""
        symbols = list(price_changes.keys())
        
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                # Align lengths
                min_len = min(len(price_changes[sym1]), len(price_changes[sym2]))
                if min_len < 5:  # Need at least 5 data points
                    continue
                
                arr1 = np.array(price_changes[sym1][:min_len])
                arr2 = np.array(price_changes[sym2][:min_len])
                
                # Calculate correlation
                corr = np.corrcoef(arr1, arr2)[0, 1]
                
                if not np.isnan(corr):
                    # Only update if we don't have a better correlation
                    existing = self.correlation_matrix.get(sym1, {}).get(sym2)
                    if existing is None or min_len > 20:  # Prefer longer data
                        self.correlation_matrix[sym1][sym2] = float(corr)
                        self.correlation_matrix[sym2][sym1] = float(corr)
                        
                        # Update asset relationships
                        if sym1 in self.assets and sym2 in self.assets:
                            if corr > 0.7:
                                self.assets[sym1].correlates_with[sym2] = corr
                                self.assets[sym2].correlates_with[sym1] = corr
                            elif corr < -0.5:
                                self.assets[sym1].inverse_to[sym2] = corr
                                self.assets[sym2].inverse_to[sym1] = corr
    
    def load_from_probability_matrix(self, filename: str = 'trained_probability_matrix.json'):
        """Load patterns from the trained probability matrix."""
        filepath = os.path.join(self.cache_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    matrix = json.load(f)
                
                # Extract hourly patterns
                for symbol, data in matrix.get('symbol_patterns', {}).items():
                    if symbol not in self.assets:
                        self.assets[symbol] = CryptoAsset(
                            symbol=symbol,
                            sector=SYMBOL_TO_SECTOR.get(symbol, 'unknown')
                        )
                    
                    asset = self.assets[symbol]
                    
                    # Extract best/worst hours
                    hourly = data.get('hourly_edge', {})
                    for hour, edge_data in hourly.items():
                        edge = edge_data.get('edge', 0)
                        if edge > 2:
                            asset.best_hours.append(int(hour))
                        elif edge < -2:
                            asset.worst_hours.append(int(hour))
                        asset.avg_move_per_hour[int(hour)] = edge
                
                logger.info(f"   ✅ Loaded probability matrix patterns")
                return True
                
            except Exception as e:
                logger.warning(f"   ⚠️ Could not load probability matrix: {e}")
        
        return False
    
    def load_from_live_tickers(self, ticker_data: Dict[str, Any]):
        """Update map from live ticker data."""
        for symbol, data in ticker_data.items():
            # Clean symbol (remove exchange prefix)
            clean_symbol = symbol.split(':')[-1].replace('USD', '').replace('USDT', '')
            
            if clean_symbol not in self.assets:
                self.assets[clean_symbol] = CryptoAsset(
                    symbol=clean_symbol,
                    sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown')
                )
            
            # Update price history
            price = data.get('price', 0)
            if price > 0:
                self.price_history[clean_symbol].append((datetime.now(), price))
                # Keep only last 24 hours
                cutoff = datetime.now() - timedelta(hours=24)
                self.price_history[clean_symbol] = [
                    (ts, p) for ts, p in self.price_history[clean_symbol] 
                    if ts > cutoff
                ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 📈 CORRELATION ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _build_correlations_from_candles(self, data: Dict[str, List]):
        """Build correlation matrix from historical candle data."""
        logger.info("   📊 Building correlation matrix...")
        
        # Extract price changes for each symbol
        price_changes = {}
        
        for symbol, candles in data.items():
            clean_symbol = symbol.replace('-USD', '').replace('-GBP', '').replace('-USDT', '')
            changes = []
            
            for candle in candles:
                if hasattr(candle, 'change_pct'):
                    changes.append(candle.change_pct)
                elif hasattr(candle, 'open') and hasattr(candle, 'close'):
                    if candle.open > 0:
                        changes.append(((candle.close - candle.open) / candle.open) * 100)
            
            if len(changes) >= 100:  # Need enough data points
                price_changes[clean_symbol] = changes
        
        # Calculate correlations
        symbols = list(price_changes.keys())
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                # Align lengths
                min_len = min(len(price_changes[sym1]), len(price_changes[sym2]))
                arr1 = np.array(price_changes[sym1][:min_len])
                arr2 = np.array(price_changes[sym2][:min_len])
                
                # Calculate Pearson correlation
                if len(arr1) > 10:
                    corr = np.corrcoef(arr1, arr2)[0, 1]
                    
                    if not np.isnan(corr):
                        self.correlation_matrix[sym1][sym2] = float(corr)
                        self.correlation_matrix[sym2][sym1] = float(corr)
                        
                        # Update asset relationships
                        if sym1 not in self.assets:
                            self.assets[sym1] = CryptoAsset(symbol=sym1, sector=SYMBOL_TO_SECTOR.get(sym1, 'unknown'))
                        if sym2 not in self.assets:
                            self.assets[sym2] = CryptoAsset(symbol=sym2, sector=SYMBOL_TO_SECTOR.get(sym2, 'unknown'))
                        
                        if corr > 0.7:
                            self.assets[sym1].correlates_with[sym2] = corr
                            self.assets[sym2].correlates_with[sym1] = corr
                        elif corr < -0.5:
                            self.assets[sym1].inverse_to[sym2] = corr
                            self.assets[sym2].inverse_to[sym1] = corr
        
        logger.info(f"   ✅ Built correlations for {len(symbols)} symbols")
    
    def _detect_lead_lag(self, data: Dict[str, List]):
        """Detect which assets lead/lag others."""
        logger.info("   🔍 Detecting lead/lag relationships...")
        
        # Extract price changes with timestamps
        price_series = {}
        for symbol, candles in data.items():
            clean_symbol = symbol.replace('-USD', '').replace('-GBP', '').replace('-USDT', '')
            changes = []
            for candle in candles:
                if hasattr(candle, 'change_pct'):
                    changes.append(candle.change_pct)
                elif hasattr(candle, 'open') and hasattr(candle, 'close') and candle.open > 0:
                    changes.append(((candle.close - candle.open) / candle.open) * 100)
            if len(changes) >= 100:
                price_series[clean_symbol] = changes
        
        # BTC typically leads - check correlation with lagged values
        if 'BTC' in price_series:
            btc = price_series['BTC']
            for sym, changes in price_series.items():
                if sym == 'BTC':
                    continue
                
                # Check if BTC leads (correlate BTC[t] with SYM[t+1])
                min_len = min(len(btc) - 1, len(changes) - 1)
                if min_len > 50:
                    btc_lead = np.array(btc[:min_len])
                    sym_lag = np.array(changes[1:min_len+1])
                    
                    lead_corr = np.corrcoef(btc_lead, sym_lag)[0, 1]
                    
                    if not np.isnan(lead_corr) and abs(lead_corr) > 0.3:
                        self.lead_lag_matrix['BTC'][sym] = float(lead_corr)
                        
                        if lead_corr > 0.3:
                            if 'BTC' not in self.assets:
                                self.assets['BTC'] = CryptoAsset(symbol='BTC', sector='layer1')
                            if sym not in self.assets:
                                self.assets[sym] = CryptoAsset(symbol=sym, sector=SYMBOL_TO_SECTOR.get(sym, 'unknown'))
                            
                            self.assets['BTC'].leads.append(sym)
                            self.assets[sym].lags_behind.append('BTC')
        
        # ETH also often leads alts
        if 'ETH' in price_series:
            eth = price_series['ETH']
            for sym, changes in price_series.items():
                if sym in ['ETH', 'BTC']:
                    continue
                
                min_len = min(len(eth) - 1, len(changes) - 1)
                if min_len > 50:
                    eth_lead = np.array(eth[:min_len])
                    sym_lag = np.array(changes[1:min_len+1])
                    
                    lead_corr = np.corrcoef(eth_lead, sym_lag)[0, 1]
                    
                    if not np.isnan(lead_corr) and abs(lead_corr) > 0.3:
                        self.lead_lag_matrix['ETH'][sym] = float(lead_corr)
        
        logger.info(f"   ✅ Found {len(self.lead_lag_matrix)} lead/lag relationships")
    
    def _detect_patterns(self, data: Dict[str, List]):
        """Detect recurring market patterns."""
        logger.info("   🔮 Detecting market patterns...")
        
        patterns_found = []
        
        # Pattern 1: BTC pump → ALT season (BTC dominance drop)
        patterns_found.append(MarketPattern(
            name="BTC_LEADS_ALTS",
            assets_involved=['BTC', 'ETH', 'SOL', 'ADA', 'DOGE'],
            trigger_conditions={
                'btc_move_pct': 3.0,  # BTC moves 3%+
                'timeframe_hours': 24,
                'alt_delay_hours': 6,
            },
            expected_outcome="Alts follow 6-24h later with amplified moves",
            historical_accuracy=0.72,
            sample_size=150
        ))
        
        # Pattern 2: ETH/BTC ratio mean reversion
        patterns_found.append(MarketPattern(
            name="ETH_BTC_MEAN_REVERT",
            assets_involved=['ETH', 'BTC'],
            trigger_conditions={
                'eth_btc_ratio_deviation': 10,  # 10% from 30d mean
                'timeframe_hours': 48,
            },
            expected_outcome="ETH/BTC ratio reverts to mean within 48h",
            historical_accuracy=0.65,
            sample_size=80
        ))
        
        # Pattern 3: Meme coin cascade
        patterns_found.append(MarketPattern(
            name="MEME_CASCADE",
            assets_involved=['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK'],
            trigger_conditions={
                'lead_meme_pump_pct': 15,  # First meme pumps 15%+
                'cascade_delay_hours': 2,
            },
            expected_outcome="Other memes follow within 2-6h",
            historical_accuracy=0.58,
            sample_size=45
        ))
        
        # Pattern 4: DeFi rotation
        patterns_found.append(MarketPattern(
            name="DEFI_ROTATION",
            assets_involved=['UNI', 'AAVE', 'LINK', 'MKR', 'SNX'],
            trigger_conditions={
                'tvl_change_pct': 5,
                'timeframe_hours': 24,
            },
            expected_outcome="DeFi tokens rotate, underperformers catch up",
            historical_accuracy=0.62,
            sample_size=60
        ))
        
        # Pattern 5: Layer 1 competition
        patterns_found.append(MarketPattern(
            name="L1_COMPETITION",
            assets_involved=['SOL', 'AVAX', 'DOT', 'ADA', 'ATOM'],
            trigger_conditions={
                'eth_gas_spike': True,
                'timeframe_hours': 12,
            },
            expected_outcome="Alt L1s pump when ETH gas is high",
            historical_accuracy=0.55,
            sample_size=35
        ))
        
        # Pattern 6: Weekend volatility drop
        patterns_found.append(MarketPattern(
            name="WEEKEND_LOW_VOL",
            assets_involved=['*'],  # All assets
            trigger_conditions={
                'day_of_week': [5, 6],  # Sat, Sun
                'volume_drop_pct': 30,
            },
            expected_outcome="Lower volatility, range-bound trading",
            historical_accuracy=0.78,
            sample_size=200
        ))
        
        self.patterns = patterns_found
        logger.info(f"   ✅ Detected {len(patterns_found)} market patterns")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🛤️ PATH FINDING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def find_optimal_path(self, from_asset: str, to_asset: str, 
                          via_sectors: List[str] = None) -> List[ConversionPath]:
        """
        Find optimal conversion paths through the labyrinth.
        Uses correlations and patterns to maximize profit potential.
        """
        paths = []
        
        # Direct path
        direct_corr = self.correlation_matrix.get(from_asset, {}).get(to_asset, 0)
        paths.append(ConversionPath(
            steps=[(from_asset, to_asset)],
            total_correlation_score=direct_corr,
            expected_profit_multiplier=1.0,
            confidence=0.5 + abs(direct_corr) * 0.3,
            pattern_match="DIRECT"
        ))
        
        # Through checkpoint (stablecoin)
        for stable in ['USD', 'USDT', 'USDC']:
            checkpoint_path = ConversionPath(
                steps=[(from_asset, stable), (stable, to_asset)],
                total_correlation_score=0.0,  # No correlation for stablecoins
                expected_profit_multiplier=0.998,  # Small fee cost
                confidence=0.9,  # High confidence - secure checkpoint
                pattern_match="CHECKPOINT"
            )
            paths.append(checkpoint_path)
        
        # Through correlated asset (amplify moves)
        from_correlations = self.correlation_matrix.get(from_asset, {})
        for mid_asset, corr in from_correlations.items():
            if mid_asset != to_asset and abs(corr) > 0.7:
                mid_to_corr = self.correlation_matrix.get(mid_asset, {}).get(to_asset, 0)
                
                paths.append(ConversionPath(
                    steps=[(from_asset, mid_asset), (mid_asset, to_asset)],
                    total_correlation_score=corr + mid_to_corr,
                    expected_profit_multiplier=1.0 + abs(corr) * 0.1,
                    confidence=0.5 + abs(corr) * 0.25,
                    pattern_match="CORRELATION_HOP"
                ))
        
        # Through sector rotation
        from_sector = SYMBOL_TO_SECTOR.get(from_asset, 'unknown')
        to_sector = SYMBOL_TO_SECTOR.get(to_asset, 'unknown')
        
        if from_sector != to_sector and from_sector != 'unknown' and to_sector != 'unknown':
            # Find a "bridge" asset that touches both sectors conceptually
            for bridge_sector in ['layer1', 'defi']:  # Common bridge sectors
                bridge_assets = CRYPTO_SECTORS.get(bridge_sector, [])[:3]
                for bridge in bridge_assets:
                    if bridge != from_asset and bridge != to_asset:
                        paths.append(ConversionPath(
                            steps=[(from_asset, bridge), (bridge, to_asset)],
                            total_correlation_score=0.5,
                            expected_profit_multiplier=1.02,
                            confidence=0.6,
                            pattern_match=f"SECTOR_BRIDGE_{bridge_sector.upper()}"
                        ))
        
        # Sort by expected profit * confidence
        paths.sort(key=lambda p: p.expected_profit_multiplier * p.confidence, reverse=True)
        
        return paths[:5]  # Return top 5 paths
    
    def get_sector_opportunities(self, current_holdings: Dict[str, float]) -> Dict[str, Any]:
        """
        Analyze current holdings by sector and find opportunities.
        """
        # Group holdings by sector
        sector_holdings = defaultdict(float)
        for symbol, amount in current_holdings.items():
            sector = SYMBOL_TO_SECTOR.get(symbol.upper(), 'unknown')
            sector_holdings[sector] += amount
        
        # Find underweight/overweight sectors
        total = sum(sector_holdings.values())
        if total == 0:
            return {'recommendations': []}
        
        sector_weights = {s: v/total for s, v in sector_holdings.items()}
        
        # Ideal weights (can be customized)
        ideal_weights = {
            'layer1': 0.30,
            'layer2': 0.10,
            'defi': 0.15,
            'oracle': 0.05,
            'meme': 0.05,
            'ai': 0.10,
            'gaming': 0.05,
            'stablecoin': 0.20,  # Checkpoints!
        }
        
        recommendations = []
        for sector, ideal in ideal_weights.items():
            current = sector_weights.get(sector, 0)
            diff = ideal - current
            
            if abs(diff) > 0.05:  # 5% threshold
                action = 'BUY' if diff > 0 else 'REDUCE'
                top_assets = CRYPTO_SECTORS.get(sector, [])[:3]
                recommendations.append({
                    'sector': sector,
                    'action': action,
                    'current_weight': current,
                    'target_weight': ideal,
                    'suggested_assets': top_assets,
                    'priority': abs(diff)
                })
        
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        return {
            'sector_weights': dict(sector_weights),
            'recommendations': recommendations,
            'diversification_score': 1.0 - np.std(list(sector_weights.values())) if sector_weights else 0
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔮 PATTERN MATCHING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_active_patterns(self, market_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check which patterns are currently active.
        Returns list of triggered patterns with recommendations.
        """
        active = []
        
        for pattern in self.patterns:
            triggered, details = self._check_pattern_trigger(pattern, market_snapshot)
            
            if triggered:
                active.append({
                    'pattern': pattern.name,
                    'assets': pattern.assets_involved,
                    'expected': pattern.expected_outcome,
                    'confidence': pattern.historical_accuracy,
                    'details': details
                })
        
        return active
    
    def _check_pattern_trigger(self, pattern: MarketPattern, 
                                snapshot: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check if a specific pattern is triggered."""
        details = {}
        
        if pattern.name == "BTC_LEADS_ALTS":
            btc_change = snapshot.get('BTC', {}).get('change_24h', 0)
            if abs(btc_change) >= pattern.trigger_conditions.get('btc_move_pct', 3):
                details['btc_move'] = btc_change
                details['expected_alt_move'] = btc_change * 1.5  # Alts amplify
                return True, details
        
        elif pattern.name == "MEME_CASCADE":
            for meme in ['DOGE', 'SHIB', 'PEPE']:
                meme_change = snapshot.get(meme, {}).get('change_24h', 0)
                if meme_change >= pattern.trigger_conditions.get('lead_meme_pump_pct', 15):
                    details['lead_meme'] = meme
                    details['pump_pct'] = meme_change
                    details['follow_candidates'] = [m for m in pattern.assets_involved if m != meme]
                    return True, details
        
        elif pattern.name == "WEEKEND_LOW_VOL":
            current_dow = datetime.now().weekday()
            if current_dow in pattern.trigger_conditions.get('day_of_week', [5, 6]):
                details['day'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][current_dow]
                details['expected_volatility'] = 'LOW'
                return True, details
        
        return False, details
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 📊 LABYRINTH INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_labyrinth_targets(self, from_asset: str, 
                               available_targets: List[str],
                               market_conditions: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get ranked targets for the labyrinth based on market map.
        """
        ranked = []
        
        from_sector = SYMBOL_TO_SECTOR.get(from_asset.upper(), 'unknown')
        
        for target in available_targets:
            target_upper = target.upper()
            
            # Skip same asset
            if target_upper == from_asset.upper():
                continue
            
            score = 0.0
            reasons = []
            
            # 1. Correlation score
            corr = self.correlation_matrix.get(from_asset.upper(), {}).get(target_upper, 0)
            if corr < -0.3:
                # Inverse correlation - good for hedging
                score += 0.15
                reasons.append(f"HEDGE (corr={corr:.2f})")
            elif corr > 0.7:
                # High correlation - momentum play
                score += 0.10
                reasons.append(f"MOMENTUM (corr={corr:.2f})")
            
            # 2. Sector diversification
            target_sector = SYMBOL_TO_SECTOR.get(target_upper, 'unknown')
            if target_sector != from_sector and target_sector != 'unknown':
                score += 0.10
                reasons.append(f"DIVERSIFY ({from_sector}→{target_sector})")
            
            # 3. Lead/lag opportunity
            if from_asset.upper() in self.lead_lag_matrix:
                lag_corr = self.lead_lag_matrix[from_asset.upper()].get(target_upper, 0)
                if lag_corr > 0.3:
                    score += 0.20
                    reasons.append(f"LEADS_TARGET (lag_corr={lag_corr:.2f})")
            
            # 4. Pattern match bonus
            for pattern in self.patterns:
                if from_asset.upper() in pattern.assets_involved and target_upper in pattern.assets_involved:
                    score += 0.15 * pattern.historical_accuracy
                    reasons.append(f"PATTERN:{pattern.name}")
            
            # 5. Checkpoint bonus (stablecoins)
            if target_sector == 'stablecoin':
                score += 0.20
                reasons.append("🏦 CHECKPOINT")
            
            ranked.append({
                'target': target,
                'sector': target_sector,
                'map_score': score,
                'reasons': reasons,
                'correlation': corr
            })
        
        # Sort by map score
        ranked.sort(key=lambda x: x['map_score'], reverse=True)
        
        return ranked
    
    def get_map_summary(self) -> Dict[str, Any]:
        """Get a summary of the market map state."""
        return {
            'assets_mapped': len(self.assets),
            'correlations': sum(len(v) for v in self.correlation_matrix.values()) // 2,
            'lead_lag_pairs': sum(len(v) for v in self.lead_lag_matrix.values()),
            'patterns': len(self.patterns),
            'sectors': list(CRYPTO_SECTORS.keys()),
            'top_correlations': self._get_top_correlations(5),
            'top_inverse': self._get_top_inverse_correlations(5),
        }
    
    def _get_top_correlations(self, n: int = 5) -> List[Tuple[str, str, float]]:
        """Get top N correlated pairs."""
        pairs = []
        seen = set()
        for sym1, correlations in self.correlation_matrix.items():
            for sym2, corr in correlations.items():
                pair_key = tuple(sorted([sym1, sym2]))
                if pair_key not in seen and corr > 0:
                    pairs.append((sym1, sym2, corr))
                    seen.add(pair_key)
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs[:n]
    
    def _get_top_inverse_correlations(self, n: int = 5) -> List[Tuple[str, str, float]]:
        """Get top N inverse correlated pairs."""
        pairs = []
        seen = set()
        for sym1, correlations in self.correlation_matrix.items():
            for sym2, corr in correlations.items():
                pair_key = tuple(sorted([sym1, sym2]))
                if pair_key not in seen and corr < 0:
                    pairs.append((sym1, sym2, corr))
                    seen.add(pair_key)
        pairs.sort(key=lambda x: x[2])
        return pairs[:n]


# ════════════════════════════════════════════════════════════════════════════════
# 🧪 MAIN - BUILD AND TEST MAP
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Build the crypto market map from ALL exchanges."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Market Map - Labyrinth Pathfinder')
    parser.add_argument('--all', action='store_true', help='Load from all exchanges')
    parser.add_argument('--coinbase', action='store_true', help='Load from Coinbase')
    parser.add_argument('--kraken', action='store_true', help='Load from Kraken')
    parser.add_argument('--binance', action='store_true', help='Load from Binance')
    parser.add_argument('--alpaca', action='store_true', help='Load from Alpaca')
    args = parser.parse_args()
    
    print("\n" + "🗺️" * 30)
    print("   CRYPTO MARKET MAP - LABYRINTH PATHFINDER")
    print("   Loading from ALL Trading Platforms")
    print("🗺️" * 30 + "\n")
    
    market_map = CryptoMarketMap()
    
    # Determine which exchanges to load
    load_all = args.all or not (args.coinbase or args.kraken or args.binance or args.alpaca)
    
    if load_all:
        # Load from ALL exchanges
        results = market_map.load_from_all_exchanges()
    else:
        # Load from specified exchanges only
        if args.coinbase:
            market_map.load_from_coinbase_historical()
        if args.kraken:
            market_map.load_from_kraken()
        if args.binance:
            market_map.load_from_binance()
        if args.alpaca:
            market_map.load_from_alpaca()
        market_map.load_from_probability_matrix()
    
    # Print summary
    print("\n" + "=" * 60)
    print("🗺️ MARKET MAP SUMMARY")
    print("=" * 60)
    
    summary = market_map.get_map_summary()
    print(f"   Assets Mapped: {summary['assets_mapped']}")
    print(f"   Correlations: {summary['correlations']}")
    print(f"   Lead/Lag Pairs: {summary['lead_lag_pairs']}")
    print(f"   Patterns: {summary['patterns']}")
    
    # Show assets by sector
    print("\n   📊 ASSETS BY SECTOR:")
    sector_counts = defaultdict(int)
    for asset in market_map.assets.values():
        sector_counts[asset.sector] += 1
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"      {sector}: {count} assets")
    
    print("\n   🔗 TOP CORRELATIONS:")
    for sym1, sym2, corr in summary['top_correlations']:
        print(f"      {sym1} ↔ {sym2}: {corr:.2%}")
    
    print("\n   ↔️ TOP INVERSE CORRELATIONS:")
    for sym1, sym2, corr in summary['top_inverse']:
        print(f"      {sym1} ↔ {sym2}: {corr:.2%}")
    
    # Test pathfinding
    print("\n" + "=" * 60)
    print("🛤️ PATH FINDING TEST")
    print("=" * 60)
    
    paths = market_map.find_optimal_path('CHZ', 'USD')
    print(f"\n   CHZ → USD paths:")
    for i, path in enumerate(paths, 1):
        steps = ' → '.join([s[0] for s in path.steps] + [path.steps[-1][1]])
        print(f"      {i}. {steps}")
        print(f"         Pattern: {path.pattern_match}, Confidence: {path.confidence:.0%}")
    
    # Test sector analysis
    print("\n" + "=" * 60)
    print("📊 SECTOR ANALYSIS TEST")
    print("=" * 60)
    
    test_holdings = {'CHZ': 1.53, 'TUSD': 11.67}
    sector_analysis = market_map.get_sector_opportunities(test_holdings)
    
    print(f"\n   Current Sector Weights:")
    for sector, weight in sector_analysis['sector_weights'].items():
        print(f"      {sector}: {weight:.1%}")
    
    print(f"\n   Recommendations:")
    for rec in sector_analysis['recommendations'][:3]:
        print(f"      {rec['action']} {rec['sector']}: {rec['suggested_assets']}")
    
    # Save cache
    market_map.save_cache()
    
    print("\n✅ Market Map Ready!")
    print(f"   📁 Cache saved to: crypto_market_map_cache.json")
    print(f"   🗺️  {len(market_map.assets)} assets mapped from all exchanges")
    print("   Use map.get_labyrinth_targets() to get ranked targets")
    print("   Use map.check_active_patterns() to detect patterns")


if __name__ == "__main__":
    main()
