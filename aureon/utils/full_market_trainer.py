#!/usr/bin/env python3
"""
🧠📊 FULL MARKET TRAINER - LEARN FROM ENTIRE MARKET 📊🧠
═══════════════════════════════════════════════════════════════════════════════

Trains the Probability Matrix and Adaptive Learning from ALL exchange data:
├─ Coinbase: 1 year of historical OHLCV data (deep patterns)
├─ Kraken: Real-time ticker + pairs data (1424 pairs)
├─ Binance: 24h historical klines (3452 pairs)
├─ Alpaca: Crypto bars data (62 assets)
└─ Existing trade history (adaptive_learning_history.json)

OUTPUTS:
├─ trained_probability_matrix.json (enhanced with all data)
├─ adaptive_learning_history.json (updated with patterns)
├─ crypto_market_map_cache.json (correlations + patterns)
└─ full_market_training_report.json (comprehensive stats)

Gary Leckey & GitHub Copilot | January 2026
"Train the Brain with the Entire Market"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ════════════════════════════════════════════════════════════════════════════════
# 📦 IMPORTS
# ════════════════════════════════════════════════════════════════════════════════

# Crypto Market Map
try:
    from aureon.data_feeds.crypto_market_map import CryptoMarketMap, SYMBOL_TO_SECTOR, CRYPTO_SECTORS
    MARKET_MAP_AVAILABLE = True
except ImportError:
    CryptoMarketMap = None
    MARKET_MAP_AVAILABLE = False
    print("⚠️ CryptoMarketMap not available")

# Coinbase Historical Feed
try:
    from aureon.exchanges.coinbase_historical_feed import CoinbaseHistoricalFeed, CandleData
    COINBASE_AVAILABLE = True
except ImportError:
    CoinbaseHistoricalFeed = None
    COINBASE_AVAILABLE = False
    print("⚠️ CoinbaseHistoricalFeed not available")

# Kraken Client
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KrakenClient = None
    KRAKEN_AVAILABLE = False
    print("⚠️ KrakenClient not available")

# Binance Client
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BinanceClient = None
    BINANCE_AVAILABLE = False
    print("⚠️ BinanceClient not available")

# Alpaca Client
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    AlpacaClient = None
    ALPACA_AVAILABLE = False
    print("⚠️ AlpacaClient not available")


# ════════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class SymbolPattern:
    """Pattern data for a single symbol."""
    symbol: str
    sector: str = 'unknown'
    
    # Temporal patterns (hour of day)
    hourly_bullish_prob: Dict[int, float] = field(default_factory=dict)  # hour -> prob
    hourly_samples: Dict[int, int] = field(default_factory=dict)  # hour -> count
    
    # Day of week patterns
    daily_bullish_prob: Dict[int, float] = field(default_factory=dict)  # dow -> prob
    daily_samples: Dict[int, int] = field(default_factory=dict)  # dow -> count
    
    # Volatility patterns
    avg_volatility: float = 0.0
    volatility_by_hour: Dict[int, float] = field(default_factory=dict)
    
    # Performance
    total_samples: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    avg_move_pct: float = 0.0
    
    # From trades
    win_rate: float = 0.5
    avg_pnl: float = 0.0
    trade_count: int = 0


@dataclass
class TrainingReport:
    """Comprehensive training report."""
    timestamp: str
    version: str = '3.0'
    
    # Data sources
    sources_used: List[str] = field(default_factory=list)
    
    # Counts
    total_symbols: int = 0
    total_candles: int = 0
    total_trades: int = 0
    
    # Patterns
    symbol_patterns: Dict[str, Dict] = field(default_factory=dict)
    
    # Global patterns
    global_hourly_edge: Dict[int, float] = field(default_factory=dict)
    global_daily_edge: Dict[int, float] = field(default_factory=dict)
    
    # Correlations
    top_correlations: List[Tuple[str, str, float]] = field(default_factory=list)
    
    # Recommendations
    optimal_hours: List[int] = field(default_factory=list)
    avoid_hours: List[int] = field(default_factory=list)
    optimal_days: List[int] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════════════════
# 🧠 FULL MARKET TRAINER CLASS
# ════════════════════════════════════════════════════════════════════════════════

class FullMarketTrainer:
    """
    Trains the Probability Matrix and Adaptive Learning from ALL market data.
    """
    
    def __init__(self, cache_dir: str = None):
        """Initialize the trainer."""
        self.cache_dir = cache_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Pattern storage
        self.symbol_patterns: Dict[str, SymbolPattern] = {}
        
        # Global patterns
        self.hourly_bullish: Dict[int, List[float]] = defaultdict(list)
        self.hourly_samples: Dict[int, int] = defaultdict(int)
        self.daily_bullish: Dict[int, List[float]] = defaultdict(list)
        self.daily_samples: Dict[int, int] = defaultdict(int)
        
        # Raw candle data
        self.all_candles: Dict[str, List[Dict]] = defaultdict(list)
        
        # Trade history
        self.trade_history: List[Dict] = []
        
        # Correlations from market map
        self.correlations: Dict[str, Dict[str, float]] = {}
        
        # Exchange clients
        self.kraken = None
        self.binance = None
        self.alpaca = None
        self.market_map = None
        
        print("🧠 Full Market Trainer initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 📥 DATA LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def load_existing_trade_history(self):
        """Load existing adaptive learning history."""
        history_file = os.path.join(self.cache_dir, 'adaptive_learning_history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                
                self.trade_history = data.get('trades', [])
                print(f"   📚 Loaded {len(self.trade_history)} historical trades")
                
                # Extract patterns from trades
                for trade in self.trade_history:
                    symbol = trade.get('symbol', '').replace('USD', '').replace('USDT', '')
                    if not symbol:
                        continue
                    
                    if symbol not in self.symbol_patterns:
                        self.symbol_patterns[symbol] = SymbolPattern(
                            symbol=symbol,
                            sector=SYMBOL_TO_SECTOR.get(symbol, 'unknown') if SYMBOL_TO_SECTOR else 'unknown'
                        )
                    
                    pattern = self.symbol_patterns[symbol]
                    pattern.trade_count += 1
                    
                    pnl = trade.get('pnl', 0)
                    if pnl > 0:
                        pattern.win_rate = (pattern.win_rate * (pattern.trade_count - 1) + 1) / pattern.trade_count
                    else:
                        pattern.win_rate = (pattern.win_rate * (pattern.trade_count - 1)) / pattern.trade_count
                    
                    pattern.avg_pnl = (pattern.avg_pnl * (pattern.trade_count - 1) + pnl) / pattern.trade_count
                    
                    # Extract temporal patterns from entry time
                    entry_time = trade.get('entry_time', 0)
                    if entry_time > 0:
                        dt = datetime.fromtimestamp(entry_time)
                        hour = dt.hour
                        dow = dt.weekday()
                        
                        is_win = pnl > 0
                        self.hourly_bullish[hour].append(1.0 if is_win else 0.0)
                        self.daily_bullish[dow].append(1.0 if is_win else 0.0)
                
                return True
            except Exception as e:
                print(f"   ⚠️ Error loading trade history: {e}")
        return False
    
    def load_from_coinbase(self, pairs: List[str] = None):
        """Load historical data from Coinbase."""
        if not COINBASE_AVAILABLE:
            print("   ⚠️ Coinbase not available")
            return False
        
        try:
            feed = CoinbaseHistoricalFeed()
            
            if pairs is None:
                pairs = feed.TRADING_PAIRS
            
            print(f"   📊 Fetching Coinbase data for {len(pairs)} pairs...")
            data = feed.fetch_year_of_data(pairs)
            
            if not data:
                print("   ⚠️ No Coinbase data received")
                return False
            
            # Process candles
            for symbol, candles in data.items():
                clean_symbol = symbol.replace('-USD', '').replace('-GBP', '').replace('-USDT', '')
                
                if clean_symbol not in self.symbol_patterns:
                    self.symbol_patterns[clean_symbol] = SymbolPattern(
                        symbol=clean_symbol,
                        sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown') if SYMBOL_TO_SECTOR else 'unknown'
                    )
                
                pattern = self.symbol_patterns[clean_symbol]
                
                for candle in candles:
                    ts = candle.timestamp if hasattr(candle, 'timestamp') else datetime.now()
                    hour = ts.hour
                    dow = ts.weekday()
                    
                    is_bullish = candle.is_bullish if hasattr(candle, 'is_bullish') else candle.close > candle.open
                    change_pct = candle.change_pct if hasattr(candle, 'change_pct') else (
                        ((candle.close - candle.open) / candle.open) * 100 if candle.open > 0 else 0
                    )
                    
                    # Update pattern
                    pattern.total_samples += 1
                    if is_bullish:
                        pattern.bullish_count += 1
                    else:
                        pattern.bearish_count += 1
                    
                    # Hourly patterns
                    if hour not in pattern.hourly_bullish_prob:
                        pattern.hourly_bullish_prob[hour] = 0.5
                        pattern.hourly_samples[hour] = 0
                    
                    n = pattern.hourly_samples[hour]
                    pattern.hourly_bullish_prob[hour] = (
                        (pattern.hourly_bullish_prob[hour] * n + (1.0 if is_bullish else 0.0)) / (n + 1)
                    )
                    pattern.hourly_samples[hour] = n + 1
                    
                    # Daily patterns
                    if dow not in pattern.daily_bullish_prob:
                        pattern.daily_bullish_prob[dow] = 0.5
                        pattern.daily_samples[dow] = 0
                    
                    n = pattern.daily_samples[dow]
                    pattern.daily_bullish_prob[dow] = (
                        (pattern.daily_bullish_prob[dow] * n + (1.0 if is_bullish else 0.0)) / (n + 1)
                    )
                    pattern.daily_samples[dow] = n + 1
                    
                    # Global patterns
                    self.hourly_bullish[hour].append(1.0 if is_bullish else 0.0)
                    self.daily_bullish[dow].append(1.0 if is_bullish else 0.0)
                    
                    # Store candle for correlation analysis
                    self.all_candles[clean_symbol].append({
                        'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                        'open': candle.open,
                        'close': candle.close,
                        'change_pct': change_pct
                    })
            
            print(f"   ✅ Processed {sum(len(c) for c in self.all_candles.values())} candles from Coinbase")
            return True
            
        except Exception as e:
            print(f"   ❌ Coinbase error: {e}")
            return False
    
    def load_from_kraken(self):
        """Load data from Kraken."""
        if not KRAKEN_AVAILABLE:
            print("   ⚠️ Kraken not available")
            return False
        
        try:
            self.kraken = get_kraken_client()
            
            # Get 24h tickers
            tickers = self.kraken.get_24h_tickers()
            print(f"   🐙 Processing {len(tickers)} Kraken tickers...")
            
            for ticker in tickers:
                symbol = ticker.get('symbol', '')
                if not symbol.endswith('USD'):
                    continue
                
                clean_symbol = symbol.replace('USD', '').replace('USDT', '')
                if not clean_symbol or clean_symbol in ['USDC', 'USDT', 'DAI']:
                    continue
                
                if clean_symbol not in self.symbol_patterns:
                    self.symbol_patterns[clean_symbol] = SymbolPattern(
                        symbol=clean_symbol,
                        sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown') if SYMBOL_TO_SECTOR else 'unknown'
                    )
                
                pattern = self.symbol_patterns[clean_symbol]
                
                # Extract from ticker
                change_pct = float(ticker.get('priceChangePercent', 0) or 0)
                is_bullish = change_pct > 0
                
                pattern.total_samples += 1
                if is_bullish:
                    pattern.bullish_count += 1
                else:
                    pattern.bearish_count += 1
                
                # Current hour patterns
                hour = datetime.now().hour
                dow = datetime.now().weekday()
                
                self.hourly_bullish[hour].append(1.0 if is_bullish else 0.0)
                self.daily_bullish[dow].append(1.0 if is_bullish else 0.0)
            
            print(f"   ✅ Processed Kraken tickers")
            return True
            
        except Exception as e:
            print(f"   ❌ Kraken error: {e}")
            return False
    
    def load_from_binance(self):
        """Load historical data from Binance."""
        if not BINANCE_AVAILABLE:
            print("   ⚠️ Binance not available")
            return False
        
        try:
            self.binance = get_binance_client()
            
            # Get 24h historical klines
            historical = self.binance.get_24h_historical() if hasattr(self.binance, 'get_24h_historical') else {}
            
            if not historical:
                # Fallback: get tickers
                tickers = self.binance.get_24h_tickers()
                print(f"   🟡 Processing {len(tickers)} Binance tickers...")
                
                for ticker in tickers:
                    symbol = ticker.get('symbol', '')
                    if not (symbol.endswith('USDC') or symbol.endswith('USDT')):
                        continue
                    
                    clean_symbol = symbol.replace('USDC', '').replace('USDT', '')
                    if not clean_symbol:
                        continue
                    
                    if clean_symbol not in self.symbol_patterns:
                        self.symbol_patterns[clean_symbol] = SymbolPattern(
                            symbol=clean_symbol,
                            sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown') if SYMBOL_TO_SECTOR else 'unknown'
                        )
                    
                    pattern = self.symbol_patterns[clean_symbol]
                    change_pct = float(ticker.get('priceChangePercent', 0) or 0)
                    is_bullish = change_pct > 0
                    
                    pattern.total_samples += 1
                    if is_bullish:
                        pattern.bullish_count += 1
                    else:
                        pattern.bearish_count += 1
            else:
                print(f"   🟡 Processing {len(historical)} Binance kline histories...")
                
                for symbol, klines in historical.items():
                    clean_symbol = symbol.replace('USDC', '').replace('USDT', '').replace('USD', '')
                    if not clean_symbol:
                        continue
                    
                    if clean_symbol not in self.symbol_patterns:
                        self.symbol_patterns[clean_symbol] = SymbolPattern(
                            symbol=clean_symbol,
                            sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown') if SYMBOL_TO_SECTOR else 'unknown'
                        )
                    
                    pattern = self.symbol_patterns[clean_symbol]
                    
                    for kline in klines:
                        open_price = kline.get('open', 0)
                        close_price = kline.get('close', 0)
                        
                        if open_price > 0:
                            is_bullish = close_price > open_price
                            change_pct = ((close_price - open_price) / open_price) * 100
                            
                            pattern.total_samples += 1
                            if is_bullish:
                                pattern.bullish_count += 1
                            else:
                                pattern.bearish_count += 1
                            
                            # Extract hour from timestamp
                            ts = kline.get('timestamp', 0)
                            if ts > 0:
                                dt = datetime.fromtimestamp(ts / 1000)
                                hour = dt.hour
                                dow = dt.weekday()
                                
                                self.hourly_bullish[hour].append(1.0 if is_bullish else 0.0)
                                self.daily_bullish[dow].append(1.0 if is_bullish else 0.0)
                            
                            self.all_candles[clean_symbol].append({
                                'open': open_price,
                                'close': close_price,
                                'change_pct': change_pct
                            })
            
            print(f"   ✅ Processed Binance data")
            return True
            
        except Exception as e:
            print(f"   ❌ Binance error: {e}")
            return False
    
    def load_from_alpaca(self):
        """Load data from Alpaca."""
        if not ALPACA_AVAILABLE:
            print("   ⚠️ Alpaca not available")
            return False
        
        try:
            self.alpaca = AlpacaClient()
            
            # Get tradeable symbols
            symbols = self.alpaca.get_tradable_crypto_symbols() if hasattr(self.alpaca, 'get_tradable_crypto_symbols') else []
            
            if not symbols:
                assets = self.alpaca.get_assets(status='active', asset_class='crypto') or []
                symbols = [a.get('symbol', '') for a in assets if a.get('tradable')]
            
            print(f"   🦙 Processing {len(symbols)} Alpaca symbols...")
            
            # Try to get bars
            if hasattr(self.alpaca, 'get_crypto_bars'):
                alpaca_symbols = [s if '/' in s else f"{s}/USD" for s in symbols[:30]]
                bars_resp = self.alpaca.get_crypto_bars(alpaca_symbols, timeframe="1Hour", limit=24)
                bars = bars_resp.get('bars', bars_resp) if isinstance(bars_resp, dict) else {}
                
                for sym, bar_list in bars.items():
                    clean_symbol = sym.split('/')[0] if '/' in sym else sym.replace('USD', '')
                    
                    if clean_symbol not in self.symbol_patterns:
                        self.symbol_patterns[clean_symbol] = SymbolPattern(
                            symbol=clean_symbol,
                            sector=SYMBOL_TO_SECTOR.get(clean_symbol, 'unknown') if SYMBOL_TO_SECTOR else 'unknown'
                        )
                    
                    pattern = self.symbol_patterns[clean_symbol]
                    
                    for bar in bar_list:
                        open_price = bar.get('o', 0)
                        close_price = bar.get('c', 0)
                        
                        if open_price > 0:
                            is_bullish = close_price > open_price
                            pattern.total_samples += 1
                            if is_bullish:
                                pattern.bullish_count += 1
                            else:
                                pattern.bearish_count += 1
            
            print(f"   ✅ Processed Alpaca data")
            return True
            
        except Exception as e:
            print(f"   ❌ Alpaca error: {e}")
            return False
    
    def load_from_market_map(self):
        """Load correlations from market map."""
        if not MARKET_MAP_AVAILABLE:
            print("   ⚠️ Market Map not available")
            return False
        
        try:
            self.market_map = CryptoMarketMap()
            self.market_map._load_cache()
            
            self.correlations = dict(self.market_map.correlation_matrix)
            
            print(f"   🗺️ Loaded {sum(len(v) for v in self.correlations.values()) // 2} correlations from market map")
            return True
            
        except Exception as e:
            print(f"   ❌ Market Map error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🧠 TRAINING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def train_all(self, skip_coinbase: bool = False) -> TrainingReport:
        """
        Train from ALL data sources.
        Set skip_coinbase=True to skip the slow Coinbase 1-year fetch.
        """
        print("\n" + "🧠" * 30)
        print("   FULL MARKET TRAINER - LEARNING FROM ENTIRE MARKET")
        print("🧠" * 30 + "\n")
        
        sources_used = []
        
        # Load existing trade history
        print("📚 Loading existing trade history...")
        if self.load_existing_trade_history():
            sources_used.append('adaptive_learning_history')
        
        # Load from market map (correlations)
        print("\n🗺️ Loading market map correlations...")
        if self.load_from_market_map():
            sources_used.append('market_map')
        
        # Load from Kraken
        print("\n🐙 Loading from Kraken...")
        if self.load_from_kraken():
            sources_used.append('kraken')
        
        # Load from Binance
        print("\n🟡 Loading from Binance...")
        if self.load_from_binance():
            sources_used.append('binance')
        
        # Load from Alpaca
        print("\n🦙 Loading from Alpaca...")
        if self.load_from_alpaca():
            sources_used.append('alpaca')
        
        # Load from Coinbase (optional - takes time)
        if not skip_coinbase:
            print("\n🪙 Loading from Coinbase (1 year historical)...")
            if self.load_from_coinbase():
                sources_used.append('coinbase')
        else:
            print("\n⏭️ Skipping Coinbase (use --full for 1-year data)")
        
        # Calculate global patterns
        print("\n" + "=" * 60)
        print("📊 CALCULATING GLOBAL PATTERNS")
        print("=" * 60)
        
        report = self._calculate_patterns(sources_used)
        
        # Save results
        self._save_trained_matrix(report)
        self._update_adaptive_learning(report)
        
        return report
    
    def _calculate_patterns(self, sources: List[str]) -> TrainingReport:
        """Calculate patterns from all loaded data."""
        
        # Calculate global hourly edge
        global_hourly_edge = {}
        for hour in range(24):
            probs = self.hourly_bullish.get(hour, [])
            if probs:
                avg_prob = sum(probs) / len(probs)
                edge = (avg_prob - 0.5) * 100  # Convert to percentage points
                global_hourly_edge[hour] = edge
                
                status = "🟢" if edge > 2 else "🔴" if edge < -2 else "🟡"
                print(f"   Hour {hour:02d}: {edge:+.2f}% edge ({len(probs)} samples) {status}")
        
        # Calculate global daily edge
        print("\n   📅 DAILY PATTERNS:")
        global_daily_edge = {}
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for dow in range(7):
            probs = self.daily_bullish.get(dow, [])
            if probs:
                avg_prob = sum(probs) / len(probs)
                edge = (avg_prob - 0.5) * 100
                global_daily_edge[dow] = edge
                
                status = "🟢" if edge > 2 else "🔴" if edge < -2 else "🟡"
                print(f"   {day_names[dow]}: {edge:+.2f}% edge ({len(probs)} samples) {status}")
        
        # Find optimal hours
        optimal_hours = [h for h, e in global_hourly_edge.items() if e > 2]
        avoid_hours = [h for h, e in global_hourly_edge.items() if e < -2]
        optimal_days = [d for d, e in global_daily_edge.items() if e > 2]
        
        # Build symbol patterns dict
        symbol_patterns_dict = {}
        for symbol, pattern in self.symbol_patterns.items():
            prob = pattern.bullish_count / pattern.total_samples if pattern.total_samples > 0 else 0.5
            symbol_patterns_dict[symbol] = {
                'symbol': symbol,
                'sector': pattern.sector,
                'total_samples': pattern.total_samples,
                'bullish_prob': prob,
                'win_rate': pattern.win_rate,
                'trade_count': pattern.trade_count,
                'hourly_edge': {
                    str(h): {
                        'edge': (p - 0.5) * 100,
                        'confidence': min(pattern.hourly_samples.get(h, 0) / 100, 1.0)
                    }
                    for h, p in pattern.hourly_bullish_prob.items()
                },
                'daily_edge': {
                    str(d): {
                        'edge': (p - 0.5) * 100,
                        'confidence': min(pattern.daily_samples.get(d, 0) / 100, 1.0)
                    }
                    for d, p in pattern.daily_bullish_prob.items()
                }
            }
        
        # Get top correlations
        top_correlations = []
        seen = set()
        for sym1, corrs in self.correlations.items():
            for sym2, corr in corrs.items():
                key = tuple(sorted([sym1, sym2]))
                if key not in seen:
                    top_correlations.append((sym1, sym2, corr))
                    seen.add(key)
        top_correlations.sort(key=lambda x: abs(x[2]), reverse=True)
        
        report = TrainingReport(
            timestamp=datetime.now().isoformat(),
            sources_used=sources,
            total_symbols=len(self.symbol_patterns),
            total_candles=sum(len(c) for c in self.all_candles.values()),
            total_trades=len(self.trade_history),
            symbol_patterns=symbol_patterns_dict,
            global_hourly_edge=global_hourly_edge,
            global_daily_edge=global_daily_edge,
            top_correlations=top_correlations[:20],
            optimal_hours=optimal_hours,
            avoid_hours=avoid_hours,
            optimal_days=optimal_days
        )
        
        print(f"\n   ✅ Total Symbols: {report.total_symbols}")
        print(f"   ✅ Total Candles: {report.total_candles}")
        print(f"   ✅ Total Trades: {report.total_trades}")
        print(f"   ✅ Optimal Hours: {optimal_hours}")
        print(f"   ❌ Avoid Hours: {avoid_hours}")
        
        return report
    
    def _save_trained_matrix(self, report: TrainingReport):
        """Save the trained probability matrix."""
        matrix = {
            'version': report.version,
            'trained_at': report.timestamp,
            'data_sources': report.sources_used,
            'total_symbols': report.total_symbols,
            'total_candles': report.total_candles,
            'total_trades': report.total_trades,
            
            # Global patterns
            'hourly_edge': {
                str(h): {'edge': e, 'confidence': min(len(self.hourly_bullish.get(h, [])) / 1000, 1.0)}
                for h, e in report.global_hourly_edge.items()
            },
            'daily_edge': {
                str(d): {'edge': e, 'confidence': min(len(self.daily_bullish.get(d, [])) / 5000, 1.0)}
                for d, e in report.global_daily_edge.items()
            },
            
            # Per-symbol patterns
            'symbol_patterns': report.symbol_patterns,
            
            # Optimal conditions
            'optimal_conditions': {
                'hours': report.optimal_hours,
                'days': report.optimal_days,
            },
            'avoid_conditions': {
                'hours': report.avoid_hours,
            },
            
            # Correlations
            'top_correlations': [
                {'pair': f"{s1}-{s2}", 'correlation': c}
                for s1, s2, c in report.top_correlations[:20]
            ]
        }
        
        filename = os.path.join(self.cache_dir, 'trained_probability_matrix.json')
        with open(filename, 'w') as f:
            json.dump(matrix, f, indent=2, default=str)
        
        print(f"\n   💾 Saved trained matrix to {filename}")
    
    def _update_adaptive_learning(self, report: TrainingReport):
        """Update adaptive learning history with new patterns."""
        history_file = os.path.join(self.cache_dir, 'adaptive_learning_history.json')
        
        # Load existing
        data = {'trades': [], 'patterns': {}, 'metadata': {}}
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
            except:
                pass
        
        # Update metadata
        data['metadata'] = {
            'last_training': report.timestamp,
            'sources': report.sources_used,
            'total_symbols': report.total_symbols,
            'total_candles': report.total_candles,
            'optimal_hours': report.optimal_hours,
            'avoid_hours': report.avoid_hours,
        }
        
        # Update patterns
        data['patterns'] = {
            'hourly_edge': report.global_hourly_edge,
            'daily_edge': report.global_daily_edge,
            'symbol_count': report.total_symbols,
        }
        
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"   💾 Updated adaptive learning history")
        
        # Also save full report
        report_file = os.path.join(self.cache_dir, 'full_market_training_report.json')
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        print(f"   💾 Saved full training report to {report_file}")


# ════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Run the full market trainer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Full Market Trainer')
    parser.add_argument('--full', action='store_true', help='Include Coinbase 1-year historical (slow)')
    parser.add_argument('--quick', action='store_true', help='Quick mode - skip slow sources')
    args = parser.parse_args()
    
    trainer = FullMarketTrainer()
    
    # Train from all data
    report = trainer.train_all(skip_coinbase=not args.full)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎓 TRAINING COMPLETE!")
    print("=" * 60)
    print(f"   📊 Symbols Trained: {report.total_symbols}")
    print(f"   📈 Candles Processed: {report.total_candles}")
    print(f"   💰 Trades Analyzed: {report.total_trades}")
    print(f"   📁 Sources: {', '.join(report.sources_used)}")
    print("\n   🔗 TOP CORRELATIONS:")
    for s1, s2, c in report.top_correlations[:5]:
        print(f"      {s1} ↔ {s2}: {c:.2%}")
    print("\n   ✅ Files Updated:")
    print("      - trained_probability_matrix.json")
    print("      - adaptive_learning_history.json")
    print("      - full_market_training_report.json")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
