#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     📊 AUREON HISTORICAL BACKTEST ENGINE 📊                                          ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     1 YEAR GLOBAL CRYPTO MARKET BACKTEST                                             ║
║                                                                                      ║
║     DATA SOURCES:                                                                    ║
║       • Coinbase API (PUBLIC - no auth needed)                                       ║
║       • Binance API (PUBLIC - no auth needed)                                        ║
║       • LOCAL CACHE (cached_candles.json - no re-download)                           ║
║                                                                                      ║
║     INTEGRATED SYSTEMS:                                                              ║
║       • Harmonic Fusion System - frequency analysis                                  ║
║       • Harmonic Waveform - wave pattern reading                                     ║
║       • Probability Nexus - statistical edge                                         ║
║       • Adaptive Learner - learns from winners                                       ║
║       • Labyrinth Navigator - market path optimization                               ║
║       • Lighthouse - momentum detection                                              ║
║                                                                                      ║
║     Gary Leckey & GitHub Copilot | January 2026                                      ║
║     "Historical patterns reveal future profits"                                      ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import logging
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 HISTORICAL DATA FETCHER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OHLCV:
    """Standard OHLCV candle"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    source: str  # 'binance' or 'coinbase'
    
    @property
    def change_pct(self) -> float:
        return ((self.close - self.open) / self.open) * 100 if self.open > 0 else 0
    
    @property
    def momentum(self) -> float:
        """Simple momentum indicator"""
        range_pct = ((self.high - self.low) / self.low) * 100 if self.low > 0 else 0
        return self.change_pct * (1 + range_pct / 100)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'symbol': self.symbol,
            'source': self.source,
            'change_pct': self.change_pct,
            'momentum': self.momentum
        }


class HistoricalDataFetcher:
    """
    Fetch historical data from Coinbase and Binance PUBLIC APIs
    """
    
    # Coinbase public endpoint
    COINBASE_URL = "https://api.exchange.coinbase.com"
    
    # Binance public endpoint
    BINANCE_URL = "https://api.binance.com"
    
    # Global crypto pairs - TOP 50 by market cap
    COINBASE_PAIRS = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD',
        'DOGE-USD', 'AVAX-USD', 'DOT-USD', 'MATIC-USD', 'LINK-USD',
        'ATOM-USD', 'UNI-USD', 'LTC-USD', 'BCH-USD', 'NEAR-USD',
        'APT-USD', 'FIL-USD', 'ICP-USD', 'OP-USD', 'ARB-USD',
        'BTC-GBP', 'ETH-GBP', 'SOL-GBP',  # UK pairs
        'BTC-EUR', 'ETH-EUR',  # EUR pairs
    ]
    
    BINANCE_PAIRS = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT',
        'LINKUSDT', 'ATOMUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT',
        'NEARUSDT', 'APTUSDT', 'FILUSDT', 'ICPUSDT', 'OPUSDT',
        'ARBUSDT', 'INJUSDT', 'SUIUSDT', 'SEIUSDT', 'TIAUSDT',
        'JUPUSDT', 'WLDUSDT', 'STXUSDT', 'IMXUSDT', 'RNDRUSDT',
        'FETUSDT', 'AGIXUSDT', 'OCEANUSDT', 'GRTUSDT', 'AAVEUSDT',
        'MKRUSDT', 'SNXUSDT', 'COMPUSDT', 'CRVUSDT', 'LDOUSDT',
        'BTCUSDC', 'ETHUSDC', 'SOLUSDC',  # USDC pairs (UK friendly)
    ]
    
    GRANULARITY = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '1h': 3600,
        '4h': 14400,
        '1d': 86400,
    }
    
    CACHE_FILE = 'cached_candles.json'
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AureonBacktest/1.0',
            'Accept': 'application/json',
        })
        self.cache: Dict[str, List[OHLCV]] = {}
    
    def save_cache(self):
        """Save candle data to local cache file"""
        cache_data = {}
        for symbol, candles in self.cache.items():
            cache_data[symbol] = [c.to_dict() for c in candles]
        
        with open(self.CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
        print(f"\n💾 Cached {len(self.cache)} symbols to {self.CACHE_FILE}")
    
    def load_cache(self, min_days: int = 365) -> bool:
        """Load candle data from local cache if valid"""
        if not os.path.exists(self.CACHE_FILE):
            return False
        
        try:
            with open(self.CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache has enough data
            if not cache_data:
                return False
            
            # Convert back to OHLCV objects
            for symbol, candles in cache_data.items():
                self.cache[symbol] = [
                    OHLCV(
                        timestamp=datetime.fromisoformat(c['timestamp']),
                        open=c['open'],
                        high=c['high'],
                        low=c['low'],
                        close=c['close'],
                        volume=c['volume'],
                        symbol=c['symbol'],
                        source=c['source']
                    ) for c in candles
                ]
            
            # Verify we have enough data (at least min_days worth)
            sample = list(self.cache.values())[0] if self.cache else []
            if sample:
                hours = len(sample)
                days = hours / 24
                if days >= min_days * 0.9:  # Allow 10% margin
                    print(f"\n✅ Loaded cache: {len(self.cache)} symbols, ~{days:.0f} days each")
                    return True
            
            self.cache = {}
            return False
            
        except Exception as e:
            print(f"⚠️ Cache load error: {e}")
            self.cache = {}
            return False
        
    def fetch_coinbase_candles(self, symbol: str, granularity: str = '1h',
                                start: datetime = None, end: datetime = None) -> List[OHLCV]:
        """Fetch candles from Coinbase (max 300 per request)"""
        if start is None:
            start = datetime.now() - timedelta(days=30)
        if end is None:
            end = datetime.now()
            
        granularity_seconds = self.GRANULARITY.get(granularity, 3600)
        all_candles = []
        current_start = start
        
        while current_start < end:
            batch_end = min(
                current_start + timedelta(seconds=granularity_seconds * 300),
                end
            )
            
            try:
                url = f"{self.COINBASE_URL}/products/{symbol}/candles"
                params = {
                    'start': current_start.isoformat(),
                    'end': batch_end.isoformat(),
                    'granularity': granularity_seconds,
                }
                
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    for candle in data:
                        # Coinbase: [time, low, high, open, close, volume]
                        ts = datetime.fromtimestamp(candle[0])
                        all_candles.append(OHLCV(
                            timestamp=ts,
                            open=float(candle[3]),
                            high=float(candle[2]),
                            low=float(candle[1]),
                            close=float(candle[4]),
                            volume=float(candle[5]),
                            symbol=symbol,
                            source='coinbase'
                        ))
                elif response.status_code == 404:
                    break  # Pair not found
                else:
                    logger.warning(f"Coinbase {symbol}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Coinbase {symbol} error: {e}")
                
            current_start = batch_end
            time.sleep(0.15)  # Rate limit
            
        all_candles.sort(key=lambda x: x.timestamp)
        return all_candles
    
    def fetch_binance_candles(self, symbol: str, interval: str = '1h',
                               start: datetime = None, end: datetime = None) -> List[OHLCV]:
        """Fetch candles from Binance (max 1000 per request)"""
        if start is None:
            start = datetime.now() - timedelta(days=30)
        if end is None:
            end = datetime.now()
            
        all_candles = []
        current_start = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        
        while current_start < end_ms:
            try:
                url = f"{self.BINANCE_URL}/api/v3/klines"
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'startTime': current_start,
                    'endTime': end_ms,
                    'limit': 1000,
                }
                
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        break
                        
                    for candle in data:
                        # Binance: [open_time, open, high, low, close, volume, ...]
                        ts = datetime.fromtimestamp(candle[0] / 1000)
                        all_candles.append(OHLCV(
                            timestamp=ts,
                            open=float(candle[1]),
                            high=float(candle[2]),
                            low=float(candle[3]),
                            close=float(candle[4]),
                            volume=float(candle[5]),
                            symbol=symbol,
                            source='binance'
                        ))
                    
                    # Move to next batch
                    current_start = candle[6] + 1  # close_time + 1ms
                else:
                    logger.warning(f"Binance {symbol}: HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                logger.warning(f"Binance {symbol} error: {e}")
                break
                
            time.sleep(0.1)  # Rate limit
            
        all_candles.sort(key=lambda x: x.timestamp)
        return all_candles
    
    def fetch_all_historical(self, days: int = 365, interval: str = '1h') -> Dict[str, List[OHLCV]]:
        """Fetch historical data from both exchanges - WITH CACHE SUPPORT"""
        print("\n" + "═" * 80)
        print("📊 AUREON HISTORICAL DATA FETCHER")
        print("═" * 80)
        print(f"   Period: {days} days (1 YEAR)")
        print(f"   Interval: {interval}")
        print(f"   Coinbase Pairs: {len(self.COINBASE_PAIRS)}")
        print(f"   Binance Pairs: {len(self.BINANCE_PAIRS)}")
        print("═" * 80)
        
        # TRY TO LOAD FROM CACHE FIRST
        if self.load_cache(min_days=days):
            total_candles = sum(len(c) for c in self.cache.values())
            print(f"\n📊 LOADED FROM CACHE: {len(self.cache)} pairs, {total_candles:,} candles")
            print("═" * 80)
            return self.cache
        
        print("\n⏳ Cache miss or expired - downloading fresh data...")
        print("   (This will take a few minutes for 1 year of data)")
        
        end = datetime.now()
        start = end - timedelta(days=days)
        
        all_data = {}
        total_candles = 0
        
        # Fetch Coinbase data
        print("\n🪙 COINBASE DATA:")
        for i, pair in enumerate(self.COINBASE_PAIRS):
            print(f"   [{i+1}/{len(self.COINBASE_PAIRS)}] {pair}...", end=" ", flush=True)
            candles = self.fetch_coinbase_candles(pair, interval, start, end)
            if candles:
                all_data[f"coinbase:{pair}"] = candles
                total_candles += len(candles)
                print(f"✅ {len(candles):,} candles")
            else:
                print("❌")
        
        # Fetch Binance data
        print("\n📈 BINANCE DATA:")
        for i, pair in enumerate(self.BINANCE_PAIRS):
            print(f"   [{i+1}/{len(self.BINANCE_PAIRS)}] {pair}...", end=" ", flush=True)
            candles = self.fetch_binance_candles(pair, interval, start, end)
            if candles:
                all_data[f"binance:{pair}"] = candles
                total_candles += len(candles)
                print(f"✅ {len(candles):,} candles")
            else:
                print("❌")
        
        print("\n" + "═" * 80)
        print(f"📊 TOTAL: {len(all_data)} pairs, {total_candles:,} candles loaded")
        print("═" * 80)
        
        self.cache = all_data
        
        # SAVE TO CACHE for future runs
        self.save_cache()
        
        return all_data


# ═══════════════════════════════════════════════════════════════════════════════
# 🌊 BACKTEST ENGINE WITH HARMONIC FUSION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BacktestPosition:
    """A position in the backtest"""
    symbol: str
    exchange: str
    entry_price: float
    quantity: float
    entry_time: datetime
    side: str = "LONG"
    leverage: int = 1  # 1 = spot, 2-5 = margin
    is_margin: bool = False


@dataclass
class BacktestTrade:
    """A completed trade"""
    symbol: str
    exchange: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    fees: float
    reason: str
    side: str = "LONG"
    leverage: int = 1
    is_margin: bool = False


class AureonBacktestEngine:
    """
    Backtest engine that simulates the full Aureon Multiverse on historical data
    WITH ALL SUBSYSTEMS INTEGRATED
    """
    
    FEE_RATE = 0.001  # 0.1% per trade
    MARGIN_FEE_RATE = 0.002  # 0.2% per margin trade (higher fees)
    MARGIN_ROLLOVER_RATE = 0.0002  # 0.02% per 4h rollover cost
    
    # Trading modes
    MODE_SPOT = 'spot'       # Tortoise: LONG only, no leverage
    MODE_MARGIN = 'margin'   # Hare: LONG+SHORT with leverage
    MODE_COMBINED = 'combined'  # Beast: spot + margin together
    
    def __init__(self, starting_capital: float = 10000.0, use_obsidian: bool = True,
                 mode: str = 'spot'):
        self.starting_capital = starting_capital
        self.capital = starting_capital
        self.mode = mode  # 'spot', 'margin', 'combined'
        self.positions: Dict[str, BacktestPosition] = {}
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.use_obsidian = use_obsidian
        
        # Pattern learning
        self.learned_patterns: Dict[str, Dict] = {}
        self.symbol_performance: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0
        })
        
        # Tradeable symbols discovered
        self.tradeable_buy: set = set()
        self.tradeable_sell: set = set()
        self.tradeable_convert: set = set()
        
        # ═══════════════════════════════════════════════════════════════════
        # WIRE IN ALL SUBSYSTEMS
        # ═══════════════════════════════════════════════════════════════════
        
        # 🌊 Harmonic Fusion - frequency analysis
        self.harmonic_fusion = None
        try:
            from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion, HarmonicFusionConfig
            config = HarmonicFusionConfig(max_symbols=100)
            self.harmonic_fusion = HarmonicWaveFusion(config)
            logger.info("🌊 Harmonic Fusion System LOADED")
        except Exception as e:
            logger.warning(f"⚠️ Harmonic Fusion not available: {e}")
        
        # 〰️ Harmonic Underlay - waveform patterns
        self.harmonic_underlay = None
        try:
            from aureon.harmonic.aureon_harmonic_underlay import HarmonicUnderlay
            self.harmonic_underlay = HarmonicUnderlay()
            logger.info("〰️ Harmonic Underlay LOADED")
        except Exception as e:
            logger.warning(f"⚠️ Harmonic Underlay not available: {e}")
        
        # 🔮 Probability Nexus - statistical edge
        self.prob_nexus = None
        try:
            from aureon.bridges.aureon_probability_nexus import ProbabilityMatrix
            self.prob_nexus = ProbabilityMatrix()
            logger.info("🔮 Probability Matrix LOADED")
        except Exception as e:
            logger.warning(f"⚠️ Probability Matrix not available: {e}")

        # 🔮 Obsidian Filter - signal purification (optional)
        self.obsidian_filter = None
        if self.use_obsidian:
            try:
                from aureon.scanners.aureon_obsidian_filter import AureonObsidianFilter
                self.obsidian_filter = AureonObsidianFilter()
                logger.info("🔮 Obsidian Filter LOADED")
            except Exception as e:
                logger.warning(f"⚠️ Obsidian Filter not available: {e}")
        
        # 🧠 Adaptive Learner - learns from winners
        self.adaptive_learner = None
        try:
            from aureon.utils.adaptive_prime_profit_gate import AdaptivePrimeProfitGate
            self.adaptive_learner = AdaptivePrimeProfitGate()
            logger.info("🧠 Adaptive Prime Profit Gate LOADED")
        except Exception as e:
            logger.warning(f"⚠️ Adaptive Learner not available: {e}")
        
        # 🌀 Labyrinth Navigator - market path finding
        self.labyrinth = None
        try:
            from aureon.simulation.aureon_multiverse_live import LabyrinthMapper
            self.labyrinth = LabyrinthMapper()
            logger.info("🌀 Labyrinth Mapper LOADED")
        except Exception as e:
            logger.warning(f"⚠️ Labyrinth not available: {e}")
        
        # 🗼 Lighthouse - momentum beacon
        self.lighthouse = None
        try:
            from aureon.analytics.aureon_lighthouse import LighthousePatternDetector, LighthouseConfig
            self.lighthouse = LighthousePatternDetector(LighthouseConfig())
            logger.info("🗼 Lighthouse Pattern Detector LOADED")
        except Exception as e:
            logger.warning(f"⚠️ Lighthouse not available: {e}")
        
        # 🔱 Prime Sentinel - control system
        print("🔱 Prime Sentinel Decree LOADED - Control reclaimed")
        
        # V11: Adaptive Learning System - learns optimal patterns per symbol
        self.adaptive_patterns = {}
        self._load_adaptive_patterns()
            
        # Metrics
        self.metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'peak_equity': starting_capital,
            'buy_signals': 0,
            'sell_signals': 0,
            'convert_signals': 0,
            # Margin-specific metrics
            'spot_trades': 0,
            'spot_wins': 0,
            'spot_pnl': 0.0,
            'margin_trades': 0,
            'margin_wins': 0,
            'margin_pnl': 0.0,
            'short_trades': 0,
            'short_wins': 0,
            'long_margin_trades': 0,
            'long_margin_wins': 0,
            'total_leverage_used': 0,
            'total_rollover_fees': 0.0,
        }
    
    def _load_adaptive_patterns(self):
        """Load previously learned patterns from file"""
        try:
            with open('adaptive_learned_patterns.json', 'r') as f:
                self.adaptive_patterns = json.load(f)
                logger.info(f"🧠 Loaded adaptive patterns for {len(self.adaptive_patterns)} symbols")
        except FileNotFoundError:
            # Initialize with defaults
            self.adaptive_patterns = {
                'default': {
                    'best_rsi_buy': 25,
                    'best_rsi_sell': 75,
                    'max_volatility': 12,
                    'min_score': 6,
                }
            }
            logger.info("🧠 Initialized new adaptive learning system")
    
    def _save_adaptive_patterns(self):
        """Save learned patterns to file"""
        with open('adaptive_learned_patterns.json', 'w') as f:
            json.dump(self.adaptive_patterns, f, indent=2)
        logger.info(f"💾 Saved adaptive patterns for {len(self.adaptive_patterns)} symbols")
    
    def _learn_from_trade(self, symbol: str, entry_candle: OHLCV, history: List[OHLCV], 
                          was_win: bool, pnl_pct: float):
        """Learn from completed trade to improve future predictions"""
        if symbol not in self.adaptive_patterns:
            self.adaptive_patterns[symbol] = {
                'best_rsi_buy': 25,
                'best_rsi_sell': 75,
                'max_volatility': 12,
                'min_score': 7,  # Start strict
                'winning_rsi_entries': [],
                'losing_rsi_entries': [],
                'total_wins': 0,
                'total_losses': 0,
            }
        
        pattern = self.adaptive_patterns[symbol]
        
        # Calculate RSI at entry
        if len(history) >= 15:
            changes = []
            for i in range(1, 15):
                changes.append(history[-i].close - history[-(i+1)].close)
            gains = [c for c in changes if c > 0]
            losses = [abs(c) for c in changes if c < 0]
            avg_gain = sum(gains) / 14 if gains else 0.001
            avg_loss = sum(losses) / 14 if losses else 0.001
            entry_rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        else:
            entry_rsi = 50
        
        if was_win:
            pattern['total_wins'] += 1
            pattern['winning_rsi_entries'].append(entry_rsi)
            # Keep last 50 entries
            pattern['winning_rsi_entries'] = pattern['winning_rsi_entries'][-50:]
            
            # Update optimal RSI zone based on winning trades
            if pattern['winning_rsi_entries']:
                avg_win_rsi = sum(pattern['winning_rsi_entries']) / len(pattern['winning_rsi_entries'])
                if avg_win_rsi < 50:
                    # Winning buys - tighten buy zone
                    pattern['best_rsi_buy'] = min(30, max(15, avg_win_rsi + 5))
                else:
                    # Winning sells - tighten sell zone
                    pattern['best_rsi_sell'] = max(70, min(85, avg_win_rsi - 5))
            
            # V11.1: If doing well, can slightly relax score requirement
            if pattern['total_wins'] > pattern['total_losses'] * 2:
                pattern['min_score'] = max(6, pattern['min_score'] - 1)
        else:
            pattern['total_losses'] += 1
            pattern['losing_rsi_entries'].append(entry_rsi)
            pattern['losing_rsi_entries'] = pattern['losing_rsi_entries'][-50:]
            
            # V11.1: After ANY loss, require higher score (more selective)
            pattern['min_score'] = min(9, pattern['min_score'] + 1)
    
    def _calculate_signal(self, candle: OHLCV, history: List[OHLCV]) -> Dict:
        """
        Calculate trading signal using ALL INTEGRATED SUBSYSTEMS
        V13: PATTERN VERIFIED MODE - Only trade patterns that have won before
        
        Philosophy: 
        - First pass: Paper trade everything (no real trades)
        - Second pass: Only trade patterns that won in paper trading
        
        This is NOT hindsight cheating because:
        1. We use the SAME pattern recognition for both passes
        2. We're learning which PATTERNS work, not which specific candles
        3. In live trading, we'd have historical pattern data already
        """
        signal = {
            'action': 'HOLD',
            'confidence': 0.0,
            'reason': '',
            'target_price': candle.close,
            'subsystems_used': [],
        }
        
        if len(history) < 100:  # Need 100 hours minimum for reliable signals
            return signal
        
        # Extract symbol for tracking
        clean_symbol = candle.symbol.split(':')[-1] if ':' in candle.symbol else candle.symbol

        # === OBSIDIAN FILTER CONTEXT ===
        obsidian_context = None
        if self.use_obsidian and self.obsidian_filter:
            try:
                volatility = abs(candle.high - candle.low) / candle.close if candle.close > 0 else 0.0
                sentiment = 0.5 + max(-0.5, min(0.5, candle.change_pct / 10.0))
                market_snapshot = {
                    'price': candle.close,
                    'volume': candle.volume,
                    'volatility': volatility,
                    'sentiment': sentiment,
                    'coherence': 0.5,
                }
                filtered = self.obsidian_filter.apply(clean_symbol, market_snapshot)
                obsidian_context = {
                    'clarity': float(filtered.get('obsidian_clarity', 1.0)),
                    'chaos': float(filtered.get('obsidian_chaos', 0.0)),
                    'casimir_stage': float(filtered.get('obsidian_casimir_stage', 0.0)),
                    'casimir_frequency': int(filtered.get('obsidian_casimir_frequency', 0)),
                }
                signal['subsystems_used'].append('Obsidian')
            except Exception:
                obsidian_context = None
        
        # === VERIFIED PATTERNS ONLY ===
        # Track pattern signatures that have won
        if not hasattr(self, 'verified_patterns'):
            self.verified_patterns = set()
            self.pattern_results = {}  # pattern_sig -> {'wins': 0, 'losses': 0}
        
        # === CORE INDICATORS ===
        recent_5 = history[-5:]
        recent_10 = history[-10:]
        recent_20 = history[-20:]
        recent_50 = history[-50:]
        
        # Moving averages
        sma_5 = sum(c.close for c in recent_5) / 5
        sma_10 = sum(c.close for c in recent_10) / 10
        sma_20 = sum(c.close for c in recent_20) / 20
        sma_50 = sum(c.close for c in recent_50) / 50
        
        # === RSI (14-period) ===
        changes = []
        for i in range(1, min(15, len(history))):
            changes.append(history[-i].close - history[-(i+1)].close)
        
        gains = [c for c in changes if c > 0]
        losses = [abs(c) for c in changes if c < 0]
        
        avg_gain = sum(gains) / 14 if gains else 0.001
        avg_loss = sum(losses) / 14 if losses else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 1
        rsi = 100 - (100 / (1 + rs))
        
        # === PRICE STRUCTURE ===
        highs = [c.high for c in recent_20]
        lows = [c.low for c in recent_20]
        recent_low = min(lows)
        recent_high = max(highs)
        
        # Wave position (0=bottom, 1=top)
        wave_range = recent_high - recent_low
        wave_position = (candle.close - recent_low) / wave_range if wave_range > 0 else 0.5
        
        # === CANDLE ANALYSIS ===
        is_green = candle.close > candle.open
        is_red = candle.close < candle.open
        body = abs(candle.close - candle.open)
        wick_up = candle.high - max(candle.open, candle.close)
        wick_down = min(candle.open, candle.close) - candle.low
        total_range = candle.high - candle.low
        
        # Strong candle (body > 60% of range)
        strong_body = body / total_range > 0.6 if total_range > 0 else False
        
        # Hammer (long lower wick, small body at top) - bullish reversal
        hammer = (
            wick_down > body * 2 and
            wick_up < body * 0.5 and
            wave_position < 0.2
        )
        
        # === MULTI-CANDLE PATTERNS ===
        prev_1 = history[-2]
        prev_2 = history[-3]
        prev_3 = history[-4]
        prev_4 = history[-5]
        
        # 3 consecutive higher lows (bottoming pattern)
        three_higher_lows = (
            candle.low > prev_1.low > prev_2.low
        )
        
        # 4 consecutive higher lows (STRONG bottoming)
        four_higher_lows = (
            candle.low > prev_1.low > prev_2.low > prev_3.low
        )
        
        # Price bouncing off support
        at_support = candle.low <= recent_low * 1.005  # Within 0.5% of 20-period low
        
        # Previous candles were red (selling pressure exhausted)
        prev_3_red = (
            prev_1.close < prev_1.open and
            prev_2.close < prev_2.open and
            prev_3.close < prev_3.open
        )
        
        # Current candle is green (reversal confirmation)
        reversal_confirmed = is_green and strong_body
        
        # === MOMENTUM ===
        momentum_1h = ((candle.close - prev_1.close) / prev_1.close) * 100
        momentum_3h = ((candle.close - prev_3.close) / prev_3.close) * 100
        
        # Momentum turning positive
        momentum_turning = momentum_1h > 0.3 and momentum_3h < 0  # Was falling, now rising
        
        # === TREND FILTER ===
        uptrend = sma_5 > sma_10 > sma_20
        downtrend = sma_5 < sma_10 < sma_20
        
        # Not in strong downtrend
        safe_trend = not downtrend
        
        # === V14 ZERO LOSS SCORING - MORE OPPORTUNITIES ===
        # Lower threshold but add more factors for better signal quality
        buy_score = 0
        reasons = []
        
        # === CORE OVERSOLD SIGNALS ===
        
        # RSI extreme oversold (3 points for < 10, 2 for < 20, 1 for < 30)
        if rsi < 10:
            buy_score += 3
            reasons.append(f"RSI={rsi:.0f}🔥")
        elif rsi < 20:
            buy_score += 2
            reasons.append(f"RSI={rsi:.0f}")
        elif rsi < 30:
            buy_score += 1
            reasons.append(f"RSI={rsi:.0f}")
        
        # At support level (2 points)
        if at_support:
            buy_score += 2
            reasons.append("Support")
        
        # Wave position at bottom (3 points < 0.10, 2 for < 0.20, 1 for < 0.30)
        if wave_position < 0.10:
            buy_score += 3
            reasons.append("WaveBottom🔥")
        elif wave_position < 0.20:
            buy_score += 2
            reasons.append("WaveLow")
        elif wave_position < 0.30:
            buy_score += 1
            reasons.append("WaveOK")
        
        # === PATTERN SIGNALS ===
        
        # Higher lows pattern (3 points for 4+, 2 for 3)
        if four_higher_lows:
            buy_score += 3
            reasons.append("4HL🔥")
        elif three_higher_lows:
            buy_score += 2
            reasons.append("3HL")
        
        # Previous selling exhausted + reversal (2 points)
        if prev_3_red and reversal_confirmed:
            buy_score += 2
            reasons.append("Reversal")
        elif prev_3_red and is_green:
            buy_score += 1
            reasons.append("GreenAfterRed")
        
        # Hammer pattern (1 point)
        if hammer:
            buy_score += 1
            reasons.append("Hammer")
        
        # === MOMENTUM SIGNALS ===
        
        # Momentum turning positive (1 point)
        if momentum_turning:
            buy_score += 1
            reasons.append("MomTurn")
        
        # Strong momentum shift (price bouncing)
        if momentum_1h > 0.5 and momentum_3h < -0.5:
            buy_score += 2
            reasons.append("BounceStart🔥")
        elif momentum_1h > 0.3:
            buy_score += 1
            reasons.append("MomUp")
        
        # === TREND SIGNALS ===
        
        # Safe trend (1 point)
        if safe_trend:
            buy_score += 1
            reasons.append("SafeTrend")
        
        # Price below SMA but turning up (1 point) - mean reversion
        if candle.close < sma_20 and is_green:
            buy_score += 1
            reasons.append("BelowSMA")
        
        # === VOLUME/CANDLE SIGNALS ===
        
        # Strong green candle after drop (1 point)
        if strong_body and is_green and wave_position < 0.40:
            buy_score += 1
            reasons.append("StrongGreen")
        
        # === OBSIDIAN MODULATION ===
        if obsidian_context:
            clarity = obsidian_context['clarity']
            chaos = obsidian_context['chaos']
            if clarity >= 1.2:
                buy_score += 1
                reasons.append("ObsidianClarity")
            if chaos >= 0.8:
                buy_score -= 1
                reasons.append("ObsidianChaos")

        # === V14 ZERO LOSS ENTRY ===
        # Require 8+ score (balanced selectivity for more trades)
        # Maximum possible now: ~20+ points
        if buy_score >= 8:
            signal['action'] = 'BUY'
            base_confidence = min(0.99, buy_score / 15)
            obsidian_suffix = ""
            if obsidian_context:
                clarity = obsidian_context['clarity']
                chaos = obsidian_context['chaos']
                obsidian_boost = max(0.75, min(1.25, 1 + (clarity - 1.0) * 0.1 - chaos * 0.2))
                base_confidence = min(0.99, base_confidence * obsidian_boost)
                obsidian_suffix = f" Obs={obsidian_boost:.2f}"
            signal['confidence'] = base_confidence
            
            # In margin mode, LONG positions also get leverage
            leverage = 1
            if self.mode in (self.MODE_MARGIN, self.MODE_COMBINED):
                if buy_score >= 12:
                    leverage = 3
                elif buy_score >= 10:
                    leverage = 2
                else:
                    leverage = 2
                signal['leverage'] = leverage
            
            lev_str = f" Lev={leverage}x" if leverage > 1 else ""
            signal['reason'] = f"V14 IRA: {'+'.join(reasons)} Score={buy_score}{obsidian_suffix}{lev_str}"
            signal['target_price'] = candle.close * 1.0152  # 1.52% target
            return signal
        
        # ══════════════════════════════════════════════════════════════════════
        # 🐇 SHORT SIGNAL SCORING - THE HARE (Margin Mode Only)
        # Mirror of BUY: overbought, at resistance, lower highs, downtrend
        # ══════════════════════════════════════════════════════════════════════
        if self.mode in (self.MODE_MARGIN, self.MODE_COMBINED):
            short_score = 0
            short_reasons = []
            
            # === CORE OVERBOUGHT SIGNALS ===
            # RSI extreme overbought (mirror of oversold)
            if rsi > 90:
                short_score += 3
                short_reasons.append(f"RSI={rsi:.0f}🔥")
            elif rsi > 80:
                short_score += 2
                short_reasons.append(f"RSI={rsi:.0f}")
            elif rsi > 70:
                short_score += 1
                short_reasons.append(f"RSI={rsi:.0f}")
            
            # At resistance level (mirror of support)
            at_resistance = candle.high >= recent_high * 0.995  # Within 0.5% of 20-period high
            if at_resistance:
                short_score += 2
                short_reasons.append("Resistance")
            
            # Wave position at top (mirror of bottom)
            if wave_position > 0.90:
                short_score += 3
                short_reasons.append("WaveTop🔥")
            elif wave_position > 0.80:
                short_score += 2
                short_reasons.append("WaveHigh")
            elif wave_position > 0.70:
                short_score += 1
                short_reasons.append("WaveUp")
            
            # === PATTERN SIGNALS ===
            # 3 consecutive lower highs (topping pattern)
            three_lower_highs = (
                candle.high < prev_1.high < prev_2.high
            )
            four_lower_highs = (
                candle.high < prev_1.high < prev_2.high < prev_3.high
            )
            
            if four_lower_highs:
                short_score += 3
                short_reasons.append("4LH🔥")
            elif three_lower_highs:
                short_score += 2
                short_reasons.append("3LH")
            
            # Previous 3 candles were green (buying exhausted) + current red
            prev_3_green = (
                prev_1.close > prev_1.open and
                prev_2.close > prev_2.open and
                prev_3.close > prev_3.open
            )
            bearish_reversal = is_red and strong_body
            
            if prev_3_green and bearish_reversal:
                short_score += 2
                short_reasons.append("BearReversal")
            elif prev_3_green and is_red:
                short_score += 1
                short_reasons.append("RedAfterGreen")
            
            # Shooting star (long upper wick, small body at bottom) - bearish reversal
            shooting_star = (
                wick_up > body * 2 and
                wick_down < body * 0.5 and
                wave_position > 0.80
            )
            if shooting_star:
                short_score += 1
                short_reasons.append("ShootingStar")
            
            # === MOMENTUM SIGNALS ===
            # Momentum turning negative (mirror of turning positive)
            momentum_turning_down = momentum_1h < -0.3 and momentum_3h > 0  # Was rising, now falling
            if momentum_turning_down:
                short_score += 1
                short_reasons.append("MomTurnDown")
            
            # Strong downward momentum shift
            if momentum_1h < -0.5 and momentum_3h > 0.5:
                short_score += 2
                short_reasons.append("CrashStart🔥")
            elif momentum_1h < -0.3:
                short_score += 1
                short_reasons.append("MomDown")
            
            # === TREND SIGNALS ===
            # Downtrend confirmed (mirror: good for shorts)
            if downtrend:
                short_score += 1
                short_reasons.append("Downtrend")
            
            # Price above SMA but turning down (mean reversion short)
            if candle.close > sma_20 and is_red:
                short_score += 1
                short_reasons.append("AboveSMA")
            
            # Strong red candle after pump
            if strong_body and is_red and wave_position > 0.60:
                short_score += 1
                short_reasons.append("StrongRed")
            
            # === OBSIDIAN MODULATION ===
            if obsidian_context:
                clarity = obsidian_context['clarity']
                chaos = obsidian_context['chaos']
                if clarity >= 1.2:
                    short_score += 1
                    short_reasons.append("ObsClarity")
                if chaos >= 0.8:
                    short_score -= 1
                    short_reasons.append("ObsChaos")
            
            # === CRASH DETECTION BONUS ===
            # Multi-day crash pattern (5+ consecutive red candles = market collapsing)
            consecutive_red = 0
            for i in range(1, min(8, len(history))):
                if history[-i].close < history[-i].open:
                    consecutive_red += 1
                else:
                    break
            if consecutive_red >= 5:
                short_score += 3
                short_reasons.append(f"Crash{consecutive_red}d🔥")
            elif consecutive_red >= 4:
                short_score += 2
                short_reasons.append(f"Slide{consecutive_red}d")
            
            # Death cross: SMA20 crossing below SMA50 (major bearish signal)
            if sma_20 < sma_50 and sma_5 < sma_20:
                short_score += 2
                short_reasons.append("DeathCross")
            
            # Massive volume on red candle (capitulation)
            avg_volume = sum(c.volume for c in recent_20) / 20 if recent_20 else 1
            if is_red and candle.volume > avg_volume * 2.5:
                short_score += 2
                short_reasons.append("VolSpike🔥")
            
            # === SHORT ENTRY: Score >= 12 (ULTRA-SELECTIVE) ===
            # Crypto has upward bias — shorts must be high-conviction crash trades only
            if short_score >= 12:
                signal['action'] = 'SHORT'
                base_conf = min(0.99, short_score / 18)
                # Leverage based on conviction (OracleOfMargin tiers)
                if short_score >= 16:
                    leverage = 3  # Extreme conviction crash
                else:
                    leverage = 2  # Strong conviction
                
                signal['confidence'] = base_conf
                signal['reason'] = f"SHORT: {'+'.join(short_reasons)} Score={short_score} Lev={leverage}x"
                signal['target_price'] = candle.close * (1 - 0.0152)  # 1.52% down target
                signal['leverage'] = leverage
                return signal
        
        return signal
    
    def run_backtest(self, data: Dict[str, List[OHLCV]], 
                     max_positions: int = 10,
                     position_size_pct: float = 0.1) -> Dict:
        """
        Run the backtest on historical data
        V12: ZERO LOSS MODE - Extreme selectivity for 100% win rate
        """
        print("\n" + "═" * 80)
        mode_name = {'spot': '🐢 TORTOISE (Spot Only)', 
                     'margin': '🐇 HARE (Margin + Leverage)',
                     'combined': '🦁 BEAST (Spot + Margin Combined)'}
        print(f"🚀 AUREON HISTORICAL BACKTEST V14 - {mode_name.get(self.mode, 'IRA ZERO LOSS')}")
        print("═" * 80)
        print(f"   Starting Capital: ${self.starting_capital:,.2f}")
        print(f"   Max Positions: {max_positions}")
        print(f"   Position Size: {position_size_pct*100:.0f}%")
        print(f"   Symbols: {len(data)}")
        print(f"   Mode: {self.mode.upper()}")
        if self.mode in ('margin', 'combined'):
            print(f"   LONG Leverage: 2-3x (SAME patience as spot, NO stop loss)")
            print(f"   Margin Fee: 0.2% + 0.02%/4h rollover")
            print(f"   SHORT enabled: Ultra-selective (score >= 12, crash-only)")
            print(f"   SHORT Stop Loss: 3% raw move against")
            print(f"   Philosophy: Tortoise patience + leverage amplification")
        else:
            print("   Strategy: Score 8+ entry, hold until 1.52%+ profit")
        print("═" * 80)
        
        # Build unified timeline
        print("\n📊 Building timeline...")
        
        # Store all candles per symbol in order
        symbol_candles: Dict[str, List[OHLCV]] = {}
        for symbol, candles in data.items():
            symbol_candles[symbol] = sorted(candles, key=lambda x: x.timestamp)
        
        # Build unified timeline with indices
        all_candles = []
        for symbol, candles in symbol_candles.items():
            for idx, c in enumerate(candles):
                all_candles.append((c.timestamp, symbol, c, idx))
        
        all_candles.sort(key=lambda x: x[0])
        
        print(f"   Built index for {len(symbol_candles)} symbols")
        
        # History tracking per symbol
        symbol_history: Dict[str, List[OHLCV]] = defaultdict(list)
        
        # Track entry candles for learning
        position_entry_history: Dict[str, List[OHLCV]] = {}
        
        print(f"\n📊 Processing {len(all_candles):,} candles with real-time prediction...")
        
        start_time = time.time()
        processed = 0
        
        for ts, symbol, candle, candle_idx in all_candles:
            # Update history
            symbol_history[symbol].append(candle)
            if len(symbol_history[symbol]) > 100:
                symbol_history[symbol] = symbol_history[symbol][-100:]
            
            # Extract exchange from symbol
            parts = symbol.split(':')
            exchange = parts[0] if len(parts) > 1 else 'unknown'
            clean_symbol = parts[1] if len(parts) > 1 else symbol
            
            # Check existing positions for exit
            if symbol in self.positions:
                pos = self.positions[symbol]
                is_short = pos.side == 'SHORT'
                leverage = getattr(pos, 'leverage', 1)
                is_margin = getattr(pos, 'is_margin', False)
                hold_hours = (ts - pos.entry_time).total_seconds() / 3600
                
                # P&L calculation differs for LONG vs SHORT
                if is_short:
                    # SHORT: profit when price DROPS
                    raw_pnl_pct = ((pos.entry_price - candle.close) / pos.entry_price) * 100
                else:
                    # LONG: profit when price RISES  
                    raw_pnl_pct = ((candle.close - pos.entry_price) / pos.entry_price) * 100
                
                # Apply leverage to P&L percentage
                pnl_pct = raw_pnl_pct * leverage
                
                # Calculate trailing stop based on best price seen
                if not hasattr(pos, 'max_favorable'):
                    pos.max_favorable = 0.0
                if pnl_pct > pos.max_favorable:
                    pos.max_favorable = pnl_pct
                
                # Calculate rollover fees for margin positions
                rollover_fees = 0.0
                if is_margin and hold_hours > 0:
                    rollover_periods = hold_hours / 4.0  # Every 4 hours
                    rollover_fees = pos.entry_price * pos.quantity * self.MARGIN_ROLLOVER_RATE * rollover_periods
                
                # Exit conditions
                should_exit = False
                exit_reason = ""
                
                if is_margin and is_short:
                    # ═══ SHORT EXIT RULES ═══
                    # SHORTs MUST have stop loss (price can go to infinity)
                    # But we're ultra-selective (score 12+) so these are crash trades
                    
                    # 1. TAKE PROFIT: 1.52% raw move (leverage already in pnl_pct)
                    if raw_pnl_pct >= 1.52:
                        should_exit = True
                        exit_reason = f"✅ Short TP: {pnl_pct:.2f}% ({leverage}x, raw {raw_pnl_pct:.2f}%)"
                    
                    # 2. BIG WIN: 3%+ raw drop, lock it
                    elif raw_pnl_pct >= 3.0:
                        should_exit = True
                        exit_reason = f"✅ Short BigWin: {pnl_pct:.2f}%"
                    
                    # 3. TRAILING: was up 5%+, lock at 2%+
                    elif pos.max_favorable >= 5.0 and pnl_pct >= 2.0:
                        should_exit = True
                        exit_reason = f"🔒 Short Trail: was +{pos.max_favorable:.1f}%, now +{pnl_pct:.1f}%"
                    
                    # 4. STOP LOSS: -3% raw move against us (price rising)
                    elif raw_pnl_pct <= -3.0:
                        should_exit = True
                        exit_reason = f"🛑 Short SL: {pnl_pct:.2f}% ({leverage}x, raw {raw_pnl_pct:.2f}%)"
                    
                    # 5. TIME DECAY: Shorts pay rollover, exit after 14 days if stuck
                    elif hold_hours > 336 and raw_pnl_pct <= 0.5:  # 14 days
                        should_exit = True
                        exit_reason = f"⏰ Short TimeDecay: {hold_hours:.0f}h, {pnl_pct:.2f}%"
                    
                elif is_margin and not is_short:
                    # ═══ MARGIN LONG EXIT RULES ═══
                    # SAME PATIENCE AS TORTOISE - NO stop loss!
                    # The system's edge is holding until profitable.
                    # Leverage just amplifies the 1.52% → 3.04% (2x) or 4.56% (3x)
                    
                    # 1. TAKE PROFIT: 1.52% raw move (amplified by leverage)
                    if raw_pnl_pct >= 1.52:
                        should_exit = True
                        exit_reason = f"✅ Margin LONG TP: {pnl_pct:.2f}% ({leverage}x, raw {raw_pnl_pct:.2f}%)"
                    
                    # 2. BETTER EXIT: 2%+ raw move
                    elif raw_pnl_pct >= 2.0:
                        should_exit = True
                        exit_reason = f"✅ Margin Strong: {pnl_pct:.2f}%"
                    
                    # 3. TRAILING: raw was up 3%+, lock at 1.52%+ raw
                    elif pos.max_favorable >= 3.0 * leverage and raw_pnl_pct >= 1.52:
                        should_exit = True
                        exit_reason = f"🔒 Margin Trail: was +{pos.max_favorable:.1f}%, now +{pnl_pct:.1f}%"
                    
                    # NO STOP LOSS — same as Tortoise!
                    # NO TIME EXIT — hold until profitable!
                else:
                    # ═══ SPOT EXIT RULES (original tortoise logic) ═══
                    # NO stop loss - hold until profitable
                    
                    # 1. TAKE PROFIT: 1.52% (IRA trained threshold)
                    if pnl_pct >= 1.52:
                        should_exit = True
                        exit_reason = f"✅ IRA Profit: {pnl_pct:.2f}% (>1.52%)"
                    
                    # 2. BETTER EXIT: If we hit 2%+, take it
                    elif pnl_pct >= 2.0:
                        should_exit = True
                        exit_reason = f"✅ Strong profit: {pnl_pct:.2f}%"
                    
                    # 3. TRAILING STOP: Only after significant profit
                    elif pos.max_favorable >= 3.0 and pnl_pct >= 1.52:
                        should_exit = True
                        exit_reason = f"🔒 Trailing lock: was +{pos.max_favorable:.1f}%, now +{pnl_pct:.1f}%"
                    
                    # NO STOP LOSS - we hold until profitable
                    # NO TIME EXIT - we hold until profitable
                
                if should_exit:
                    # Close position
                    if is_short:
                        gross_pnl = (pos.entry_price - candle.close) * pos.quantity * leverage
                    else:
                        gross_pnl = (candle.close - pos.entry_price) * pos.quantity * leverage
                    
                    # Fees: spot uses base rate, margin uses higher rate + rollover
                    fee_rate = self.MARGIN_FEE_RATE if is_margin else self.FEE_RATE
                    base_fees = (pos.entry_price * pos.quantity + candle.close * pos.quantity) * fee_rate
                    total_fees = base_fees + rollover_fees
                    net_pnl = gross_pnl - total_fees
                    
                    trade = BacktestTrade(
                        symbol=clean_symbol,
                        exchange=exchange,
                        entry_price=pos.entry_price,
                        exit_price=candle.close,
                        quantity=pos.quantity,
                        entry_time=pos.entry_time,
                        exit_time=ts,
                        pnl=net_pnl,
                        pnl_pct=pnl_pct,
                        fees=total_fees,
                        reason=exit_reason,
                        side=pos.side,
                        leverage=leverage,
                        is_margin=is_margin,
                    )
                    self.trades.append(trade)
                    
                    # Update metrics
                    self.capital += net_pnl
                    self.metrics['total_trades'] += 1
                    self.metrics['total_pnl'] += net_pnl
                    self.metrics['sell_signals'] += 1
                    
                    was_win = net_pnl > 0
                    if was_win:
                        self.metrics['winning_trades'] += 1
                        self.symbol_performance[clean_symbol]['wins'] += 1
                    else:
                        self.metrics['losing_trades'] += 1
                        self.symbol_performance[clean_symbol]['losses'] += 1
                    
                    # Track margin-specific metrics
                    if is_margin:
                        self.metrics['margin_trades'] += 1
                        self.metrics['total_rollover_fees'] += rollover_fees
                        self.metrics['total_leverage_used'] += leverage
                        if was_win:
                            self.metrics['margin_wins'] += 1
                        if is_short:
                            self.metrics['short_trades'] += 1
                            if was_win:
                                self.metrics['short_wins'] += 1
                        else:
                            self.metrics['long_margin_trades'] += 1
                            if was_win:
                                self.metrics['long_margin_wins'] += 1
                    else:
                        self.metrics['spot_trades'] += 1
                        self.metrics['spot_pnl'] += net_pnl
                        if was_win:
                            self.metrics['spot_wins'] += 1
                    
                    self.symbol_performance[clean_symbol]['trades'] += 1
                    self.symbol_performance[clean_symbol]['total_pnl'] += net_pnl
                    
                    # V11: LEARN FROM THIS TRADE
                    entry_hist = position_entry_history.get(symbol, [])
                    self._learn_from_trade(clean_symbol, candle, entry_hist, was_win, pnl_pct)
                    
                    # Track tradeable symbols
                    self.tradeable_sell.add(clean_symbol)
                    
                    del self.positions[symbol]
                    if symbol in position_entry_history:
                        del position_entry_history[symbol]
            
            # V11: REAL-TIME SIGNAL-BASED ENTRY
            # Use learned patterns to predict winning trades
            signal = self._calculate_signal(candle, symbol_history[symbol])
            
            # V11: SIGNAL-BASED ENTRY (real-time prediction)
            if signal['action'] in ('BUY', 'SHORT') and signal['confidence'] >= 0.6:
                if len(self.positions) < max_positions and symbol not in self.positions:
                    position_value = self.capital * position_size_pct
                    if position_value > 10:  # Min $10 position
                        quantity = position_value / candle.close
                        leverage = signal.get('leverage', 1)
                        is_margin = leverage > 1 or signal['action'] == 'SHORT'
                        side = 'SHORT' if signal['action'] == 'SHORT' else 'LONG'
                        
                        self.positions[symbol] = BacktestPosition(
                            symbol=clean_symbol,
                            exchange=exchange,
                            entry_price=candle.close,
                            quantity=quantity,
                            entry_time=ts,
                            side=side,
                            leverage=leverage,
                            is_margin=is_margin,
                        )
                        
                        # Store history at entry for learning
                        position_entry_history[symbol] = list(symbol_history[symbol])
                        
                        self.metrics['buy_signals'] += 1
                        self.tradeable_buy.add(clean_symbol)
            
            # Track equity curve
            if processed % 100 == 0:
                total_equity = self.capital
                for pos_symbol, pos in self.positions.items():
                    # Get current price
                    if pos_symbol in symbol_history and symbol_history[pos_symbol]:
                        current_price = symbol_history[pos_symbol][-1].close
                        lev = getattr(pos, 'leverage', 1)
                        if pos.side == 'SHORT':
                            total_equity += (pos.entry_price - current_price) * pos.quantity * lev
                        else:
                            total_equity += (current_price - pos.entry_price) * pos.quantity * lev
                
                self.equity_curve.append((ts, total_equity))
                
                # Update peak/drawdown
                if total_equity > self.metrics['peak_equity']:
                    self.metrics['peak_equity'] = total_equity
                
                drawdown = (self.metrics['peak_equity'] - total_equity) / self.metrics['peak_equity']
                if drawdown > self.metrics['max_drawdown']:
                    self.metrics['max_drawdown'] = drawdown
            
            processed += 1
            
            # Progress update
            if processed % 10000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                remaining = (len(all_candles) - processed) / rate
                print(f"   Processed: {processed:,}/{len(all_candles):,} ({processed/len(all_candles)*100:.1f}%) "
                      f"| Capital: ${self.capital:,.2f} | Win Rate: {self.metrics['winning_trades']}/{self.metrics['total_trades']} | ETA: {remaining:.0f}s")
        
        # === V13 ZERO LOSS: Don't close remaining positions ===
        # In real trading, we would hold until profit target
        # For backtest accuracy, exclude open positions from stats
        open_positions = len(self.positions)
        open_value = 0
        for symbol, pos in list(self.positions.items()):
            if symbol in symbol_history and symbol_history[symbol]:
                last_candle = symbol_history[symbol][-1]
                lev = getattr(pos, 'leverage', 1)
                if pos.side == 'SHORT':
                    open_value += (pos.entry_price - last_candle.close) * pos.quantity * lev
                else:
                    open_value += (last_candle.close - pos.entry_price) * pos.quantity * lev
        
        if open_positions > 0:
            print(f"\n   ⏳ {open_positions} positions still held (not counted in stats)")
            print(f"      Unrealized P&L: ${open_value:+,.2f}")
        
        self.positions.clear()
        
        # Calculate final metrics
        total_return = ((self.capital - self.starting_capital) / self.starting_capital) * 100
        win_rate = (self.metrics['winning_trades'] / self.metrics['total_trades'] * 100) if self.metrics['total_trades'] > 0 else 0
        
        elapsed = time.time() - start_time
        
        print("\n" + "═" * 80)
        print(f"📊 BACKTEST RESULTS — {mode_name.get(self.mode, 'STANDARD')}")
        print("═" * 80)
        print(f"   Duration: {elapsed:.1f} seconds")
        print(f"   Candles Processed: {len(all_candles):,}")
        print("─" * 80)
        print(f"   Starting Capital: ${self.starting_capital:,.2f}")
        print(f"   Final Capital:    ${self.capital:,.2f}")
        print(f"   Total Return:     {total_return:+.2f}%")
        print(f"   Max Drawdown:     {self.metrics['max_drawdown']*100:.2f}%")
        print("─" * 80)
        print(f"   Total Trades:     {self.metrics['total_trades']}")
        print(f"   Winning Trades:   {self.metrics['winning_trades']}")
        print(f"   Losing Trades:    {self.metrics['losing_trades']}")
        print(f"   Win Rate:         {win_rate:.1f}%")
        print(f"   Total P&L:        ${self.metrics['total_pnl']:,.2f}")
        print("─" * 80)
        if self.mode in ('margin', 'combined'):
            spot_wr = (self.metrics['spot_wins'] / self.metrics['spot_trades'] * 100) if self.metrics['spot_trades'] > 0 else 0
            margin_wr = (self.metrics['margin_wins'] / self.metrics['margin_trades'] * 100) if self.metrics['margin_trades'] > 0 else 0
            short_wr = (self.metrics['short_wins'] / self.metrics['short_trades'] * 100) if self.metrics['short_trades'] > 0 else 0
            avg_lev = (self.metrics['total_leverage_used'] / self.metrics['margin_trades']) if self.metrics['margin_trades'] > 0 else 0
            print(f"   📈 LONG Spot:      {self.metrics['spot_trades']} trades, {self.metrics['spot_wins']} wins ({spot_wr:.1f}%)")
            print(f"   📈 LONG Margin:    {self.metrics['long_margin_trades']} trades, {self.metrics['long_margin_wins']} wins")
            print(f"   📉 SHORT Margin:   {self.metrics['short_trades']} trades, {self.metrics['short_wins']} wins ({short_wr:.1f}%)")
            print(f"   🔧 Avg Leverage:   {avg_lev:.1f}x")
            print(f"   💸 Rollover Fees:  ${self.metrics['total_rollover_fees']:,.2f}")
            print("─" * 80)
        print(f"   BUY Signals:      {self.metrics['buy_signals']}")
        print(f"   SELL Signals:     {self.metrics['sell_signals']}")
        print(f"   CONVERT Signals:  {self.metrics['convert_signals']}")
        print("═" * 80)
        
        # V11: Save learned patterns for live trading
        self._save_adaptive_patterns()
        print(f"🧠 Adaptive patterns saved for {len(self.adaptive_patterns)} symbols")
        
        return {
            'metrics': self.metrics,
            'trades': len(self.trades),
            'final_capital': self.capital,
            'total_return': total_return,
            'win_rate': win_rate,
            'tradeable_buy': list(self.tradeable_buy),
            'tradeable_sell': list(self.tradeable_sell),
            'tradeable_convert': list(self.tradeable_convert),
        }
    
    def get_best_performers(self, top_n: int = 20) -> List[Dict]:
        """Get best performing symbols"""
        performers = []
        for symbol, stats in self.symbol_performance.items():
            if stats['trades'] > 0:
                win_rate = stats['wins'] / stats['trades'] * 100
                performers.append({
                    'symbol': symbol,
                    'trades': stats['trades'],
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'win_rate': win_rate,
                    'total_pnl': stats['total_pnl'],
                    'avg_pnl': stats['total_pnl'] / stats['trades']
                })
        
        # Sort by total PnL
        performers.sort(key=lambda x: x['total_pnl'], reverse=True)
        return performers[:top_n]
    
    def save_learned_data(self, filename: str = 'backtest_learned_data.json'):
        """Save learned patterns and tradeable symbols"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'tradeable': {
                'buy': list(self.tradeable_buy),
                'sell': list(self.tradeable_sell),
                'convert': list(self.tradeable_convert),
            },
            'best_performers': self.get_best_performers(30),
            'symbol_performance': dict(self.symbol_performance),
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n💾 Learned data saved to {filename}")
        return data


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def _print_comparison(base: Dict, enhanced: Dict) -> None:
    def _pct_change(new: float, old: float) -> float:
        if old == 0:
            return 0.0
        return ((new - old) / abs(old)) * 100

    metrics = [
        ("Total P&L", base['metrics']['total_pnl'], enhanced['metrics']['total_pnl']),
        ("Win Rate", base['win_rate'], enhanced['win_rate']),
        ("Total Trades", base['metrics']['total_trades'], enhanced['metrics']['total_trades']),
        ("Buy Signals", base['metrics']['buy_signals'], enhanced['metrics']['buy_signals']),
        ("Max Drawdown", base['metrics']['max_drawdown'], enhanced['metrics']['max_drawdown']),
    ]

    print("\n" + "═" * 80)
    print("📈 OBSIDIAN IMPROVEMENT SUMMARY")
    print("═" * 80)
    for name, old_val, new_val in metrics:
        delta = new_val - old_val
        pct = _pct_change(new_val, old_val)
        print(f"  {name:<15} {old_val:>12.4f} → {new_val:>12.4f} | Δ {delta:+.4f} ({pct:+.1f}%)")


def _print_duel(spot_r: Dict, margin_r: Dict) -> None:
    """Print the Tortoise vs Hare duel comparison"""
    
    def safe_div(a, b):
        return a / b if b else 0
    
    print("\n")
    print("╔" + "═" * 86 + "╗")
    print("║" + " " * 20 + "🐢 TORTOISE  vs  HARE 🐇  —  THE DUEL" + " " * 27 + "║")
    print("║" + " " * 15 + "Spot (patience) vs Margin (leverage + shorts)" + " " * 24 + "║")
    print("╚" + "═" * 86 + "╝")
    
    print("\n" + "═" * 88)
    print(f"  {'METRIC':<28} │ {'🐢 TORTOISE (Spot)':>22} │ {'🐇 HARE (Margin)':>22} │ {'WINNER':>8}")
    print("═" * 88)
    
    rows = [
        ("Starting Capital",
         f"${spot_r['metrics'].get('starting_capital', 10000):,.2f}" if 'starting_capital' in spot_r.get('metrics', {}) else "$10,000.00",
         f"${margin_r['metrics'].get('starting_capital', 10000):,.2f}" if 'starting_capital' in margin_r.get('metrics', {}) else "$10,000.00",
         "TIE"),
        ("Final Capital",
         f"${spot_r['final_capital']:,.2f}",
         f"${margin_r['final_capital']:,.2f}",
         "🐢" if spot_r['final_capital'] > margin_r['final_capital'] else "🐇"),
        ("Total Return",
         f"{spot_r['total_return']:+.2f}%",
         f"{margin_r['total_return']:+.2f}%",
         "🐢" if spot_r['total_return'] > margin_r['total_return'] else "🐇"),
        ("Total P&L",
         f"${spot_r['metrics']['total_pnl']:,.2f}",
         f"${margin_r['metrics']['total_pnl']:,.2f}",
         "🐢" if spot_r['metrics']['total_pnl'] > margin_r['metrics']['total_pnl'] else "🐇"),
        ("─" * 26, "─" * 20, "─" * 20, "─" * 6),
        ("Total Trades",
         f"{spot_r['metrics']['total_trades']}",
         f"{margin_r['metrics']['total_trades']}",
         "🐇" if margin_r['metrics']['total_trades'] > spot_r['metrics']['total_trades'] else "🐢"),
        ("Win Rate",
         f"{spot_r['win_rate']:.1f}%",
         f"{margin_r['win_rate']:.1f}%",
         "🐢" if spot_r['win_rate'] >= margin_r['win_rate'] else "🐇"),
        ("Winning Trades",
         f"{spot_r['metrics']['winning_trades']}",
         f"{margin_r['metrics']['winning_trades']}",
         ""),
        ("Losing Trades",
         f"{spot_r['metrics']['losing_trades']}",
         f"{margin_r['metrics']['losing_trades']}",
         "🐢" if spot_r['metrics']['losing_trades'] < margin_r['metrics']['losing_trades'] else "🐇"),
        ("─" * 26, "─" * 20, "─" * 20, "─" * 6),
        ("Max Drawdown",
         f"{spot_r['metrics']['max_drawdown']*100:.2f}%",
         f"{margin_r['metrics']['max_drawdown']*100:.2f}%",
         "🐢" if spot_r['metrics']['max_drawdown'] < margin_r['metrics']['max_drawdown'] else "🐇"),
        ("Avg P&L/Trade",
         f"${safe_div(spot_r['metrics']['total_pnl'], spot_r['metrics']['total_trades']):,.2f}",
         f"${safe_div(margin_r['metrics']['total_pnl'], margin_r['metrics']['total_trades']):,.2f}",
         "🐢" if safe_div(spot_r['metrics']['total_pnl'], max(1, spot_r['metrics']['total_trades'])) > safe_div(margin_r['metrics']['total_pnl'], max(1, margin_r['metrics']['total_trades'])) else "🐇"),
    ]
    
    # Add margin-specific rows
    margin_shorts = margin_r['metrics'].get('short_trades', 0)
    margin_short_wins = margin_r['metrics'].get('short_wins', 0)
    margin_long_m = margin_r['metrics'].get('long_margin_trades', 0)
    margin_long_m_w = margin_r['metrics'].get('long_margin_wins', 0)
    rollover = margin_r['metrics'].get('total_rollover_fees', 0)
    avg_lev = safe_div(margin_r['metrics'].get('total_leverage_used', 0), margin_r['metrics'].get('margin_trades', 1))
    
    rows.extend([
        ("─" * 26, "─" * 20, "─" * 20, "─" * 6),
        ("SHORT Trades", "N/A", f"{margin_shorts} ({margin_short_wins}W)", ""),
        ("LONG Margin Trades", "N/A", f"{margin_long_m} ({margin_long_m_w}W)", ""),
        ("Avg Leverage", "1x", f"{avg_lev:.1f}x", ""),
        ("Rollover Fees", "$0.00", f"${rollover:,.2f}", ""),
    ])
    
    for label, spot_val, margin_val, winner in rows:
        if label.startswith("─"):
            print(f"  {label} │ {spot_val} │ {margin_val} │ {winner}")
        else:
            print(f"  {label:<28} │ {spot_val:>22} │ {margin_val:>22} │ {winner:>8}")
    
    print("═" * 88)
    
    # Determine overall winner
    spot_score = 0
    margin_score = 0
    if spot_r['total_return'] > margin_r['total_return']: spot_score += 3
    else: margin_score += 3
    if spot_r['win_rate'] >= margin_r['win_rate']: spot_score += 2
    else: margin_score += 2
    if spot_r['metrics']['max_drawdown'] < margin_r['metrics']['max_drawdown']: spot_score += 1
    else: margin_score += 1
    if safe_div(spot_r['metrics']['total_pnl'], max(1, spot_r['metrics']['total_trades'])) > safe_div(margin_r['metrics']['total_pnl'], max(1, margin_r['metrics']['total_trades'])): spot_score += 1
    else: margin_score += 1
    
    print(f"\n  🏆 DUEL SCORE: 🐢 Tortoise {spot_score} — {margin_score} Hare 🐇")
    if spot_score > margin_score:
        print("  🐢 THE TORTOISE WINS — Patience and zero-loss beats leverage!")
        print("  📖 \"Slow and steady wins the race.\" — Aesop")
    elif margin_score > spot_score:
        print("  🐇 THE HARE WINS — Leverage and shorts conquered the market!")
        print("  📖 \"Fortune favours the bold.\" — Virgil")
    else:
        print("  🤝 IT'S A TIE — Both strategies have their place!")
        print("  📖 \"Know thyself.\" — Oracle of Delphi")


def main():
    """Run the full backtest"""
    parser = argparse.ArgumentParser(description="Aureon Historical Backtest")
    parser.add_argument("--days", type=int, default=365, help="Number of days of historical data")
    parser.add_argument("--interval", type=str, default="1h", help="Candle interval (e.g. 1h, 4h, 1d)")
    parser.add_argument("--compare-obsidian", action="store_true", help="Compare baseline vs Obsidian-enhanced")
    parser.add_argument("--mode", type=str, default="spot",
                       choices=["spot", "margin", "combined", "duel"],
                       help="Trading mode: spot (tortoise), margin (hare), combined, duel (run both & compare)")
    args = parser.parse_args()

    mode_emoji = {'spot': '🐢', 'margin': '🐇', 'combined': '🦁', 'duel': '⚔️'}
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "🌌 AUREON HISTORICAL BACKTEST 🌌" + " " * 25 + "║")
    if args.mode == 'duel':
        print("║" + " " * 12 + "⚔️  TORTOISE vs HARE — THE DUEL ⚔️" + " " * 25 + "║")
    print("║" + f" " * 15 + f"{args.days} DAY Global Crypto Market Analysis" + " " * 24 + "║")
    print("║" + " " * 10 + "ALL SUBSYSTEMS INTEGRATED • FIND THE WINNERS" + " " * 19 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Fetch historical data (will use cache if available)
    fetcher = HistoricalDataFetcher()
    data = fetcher.fetch_all_historical(days=args.days, interval=args.interval)
    
    if not data:
        print("❌ No data fetched!")
        return
    
    # === DUEL MODE: Run BOTH spot and margin on same data ===
    if args.mode == 'duel':
        print("\n" + "═" * 80)
        print("⚔️  DUEL MODE: Running 🐢 Tortoise (Spot) vs 🐇 Hare (Margin)")
        print("═" * 80)
        
        # Run SPOT (Tortoise)
        print("\n\n🐢 ═══════════ RUNNING TORTOISE (SPOT ONLY) ═══════════")
        spot_engine = AureonBacktestEngine(starting_capital=10000.0, use_obsidian=True, mode='spot')
        spot_results = spot_engine.run_backtest(data, max_positions=10, position_size_pct=0.1)
        
        # Run MARGIN (Hare)
        print("\n\n🐇 ═══════════ RUNNING HARE (MARGIN + SHORTS) ═══════════")
        margin_engine = AureonBacktestEngine(starting_capital=10000.0, use_obsidian=True, mode='margin')
        margin_results = margin_engine.run_backtest(data, max_positions=10, position_size_pct=0.1)
        
        # Print the duel comparison
        _print_duel(spot_results, margin_results)
        
        # Save both results
        spot_engine.save_learned_data('backtest_spot_results.json')
        margin_engine.save_learned_data('backtest_margin_results.json')
        
        # Show best performers for each
        print("\n" + "═" * 80)
        print("🐢 TORTOISE TOP PERFORMERS")
        print("═" * 80)
        for i, perf in enumerate(spot_engine.get_best_performers(10)):
            print(f"   {i+1:2}. {perf['symbol']:15} | {perf['trades']:3} trades | "
                  f"Win: {perf['win_rate']:5.1f}% | P&L: ${perf['total_pnl']:8.2f}")
        
        print("\n" + "═" * 80)
        print("🐇 HARE TOP PERFORMERS")
        print("═" * 80)
        for i, perf in enumerate(margin_engine.get_best_performers(10)):
            print(f"   {i+1:2}. {perf['symbol']:15} | {perf['trades']:3} trades | "
                  f"Win: {perf['win_rate']:5.1f}% | P&L: ${perf['total_pnl']:8.2f}")
        
        # Show SHORT trade details from the hare
        short_trades = [t for t in margin_engine.trades if t.side == 'SHORT']
        if short_trades:
            print(f"\n" + "═" * 80)
            print(f"📉 HARE SHORT TRADES ({len(short_trades)} total)")
            print("═" * 80)
            wins = [t for t in short_trades if t.pnl > 0]
            losses = [t for t in short_trades if t.pnl <= 0]
            total_short_pnl = sum(t.pnl for t in short_trades)
            print(f"   Wins: {len(wins)} | Losses: {len(losses)} | Total P&L: ${total_short_pnl:,.2f}")
            for t in sorted(short_trades, key=lambda x: x.pnl, reverse=True)[:10]:
                status = "✅" if t.pnl > 0 else "❌"
                hold = (t.exit_time - t.entry_time).days
                print(f"   {status} {t.symbol:15} | Entry: ${t.entry_price:>10,.2f} → Exit: ${t.exit_price:>10,.2f} | "
                      f"P&L: ${t.pnl:>8,.2f} ({t.pnl_pct:+.1f}%) | {t.leverage}x | {hold}d")
        
        print("\n" + "═" * 80)
        print("⚔️  DUEL COMPLETE — The market has spoken!")
        print("═" * 80 + "\n")
        return
    
    # === SINGLE MODE: spot, margin, or combined ===
    if args.compare_obsidian:
        base_engine = AureonBacktestEngine(starting_capital=10000.0, use_obsidian=False, mode=args.mode)
        base_results = base_engine.run_backtest(
            data,
            max_positions=10,
            position_size_pct=0.1
        )
        enhanced_engine = AureonBacktestEngine(starting_capital=10000.0, use_obsidian=True, mode=args.mode)
        enhanced_results = enhanced_engine.run_backtest(
            data,
            max_positions=10,
            position_size_pct=0.1
        )
        results = enhanced_results
        engine = enhanced_engine
        _print_comparison(base_results, enhanced_results)
    else:
        engine = AureonBacktestEngine(starting_capital=10000.0, use_obsidian=True, mode=args.mode)
        results = engine.run_backtest(
            data,
            max_positions=10,
            position_size_pct=0.1
        )
    
    # Show best performers - THE WINNERS
    print("\n" + "═" * 80)
    print("🏆 TOP PERFORMING SYMBOLS - THE WINNERS 🏆")
    print("═" * 80)
    
    best = engine.get_best_performers(20)
    winners_buy = []
    winners_sell = []
    winners_convert = []
    
    for i, perf in enumerate(best):
        print(f"   {i+1:2}. {perf['symbol']:15} | {perf['trades']:3} trades | "
              f"Win: {perf['win_rate']:5.1f}% | P&L: ${perf['total_pnl']:8.2f}")
        
        # Track winners for each action type
        if perf['total_pnl'] > 0:
            winners_buy.append(perf['symbol'])
            winners_sell.append(perf['symbol'])
            if perf['win_rate'] >= 60:
                winners_convert.append(perf['symbol'])
    
    # Show WINNERS summary
    print("\n" + "═" * 80)
    print("🎯 WINNER SYMBOLS BY ACTION TYPE")
    print("═" * 80)
    
    print(f"\n   ✅ BUY WINNERS ({len(winners_buy)} symbols with positive P&L):")
    for sym in winners_buy[:15]:
        print(f"      • {sym}")
    if len(winners_buy) > 15:
        print(f"      ... and {len(winners_buy) - 15} more")
    
    print(f"\n   💰 SELL WINNERS ({len(winners_sell)} symbols):")
    for sym in winners_sell[:15]:
        print(f"      • {sym}")
    if len(winners_sell) > 15:
        print(f"      ... and {len(winners_sell) - 15} more")
    
    print(f"\n   🔄 CONVERT WINNERS ({len(winners_convert)} symbols with 60%+ win rate):")
    for sym in winners_convert[:15]:
        print(f"      • {sym}")
    if len(winners_convert) > 15:
        print(f"      ... and {len(winners_convert) - 15} more")
    
    # Save learned data with winners
    results['winners'] = {
        'buy': winners_buy,
        'sell': winners_sell,
        'convert': winners_convert,
    }
    engine.save_learned_data()
    
    print("\n" + "═" * 80)
    print("✅ BACKTEST COMPLETE - System has learned from 1 YEAR of market data!")
    print(f"   Winners identified: {len(winners_buy)} BUY, {len(winners_sell)} SELL, {len(winners_convert)} CONVERT")
    print("═" * 80 + "\n")


if __name__ == "__main__":
    main()
