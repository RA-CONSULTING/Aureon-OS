#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🦙🌊 AUREON ALPACA SCANNER BRIDGE 🌊🦙                                           ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                     ║
║                                                                                      ║
║     UNIFIED ALPACA INTEGRATION FOR ALL SCANNER SYSTEMS                               ║
║                                                                                      ║
║     FEATURES:                                                                        ║
║       • SSE Streaming Integration - Real-time trades/quotes/bars                     ║
║       • Dynamic Fee Tier Thresholds - Cost thresholds adjust by tier                 ║
║       • Trailing Stop Execution - Protect gains on 4th-pass trades                   ║
║       • Stock Universe Scanning - 10K+ stocks with volatility filters               ║
║       • Binance→Alpaca Bridge - Free WS scan, paid execution                         ║
║                                                                                      ║
║     SCANNER INTEGRATION:                                                             ║
║       • GlobalWaveScanner - A-Z/Z-A sweeps with SSE-backed tickers                   ║
║       • QuantumMirrorScanner - Batten Matrix with dynamic cost gates                 ║
║       • OceanScanner - Multi-exchange with trailing stop exits                       ║
║                                                                                      ║
║     Gary Leckey | January 2026 | All APIs Serve Alpaca                               ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import sys
import os

# Windows UTF-8 fix (MANDATORY)
if sys.platform == 'win32' and sys.stdout.isatty():
    # Avoid re-wrapping sys.stdout.buffer directly: on CPython this can close the
    # underlying stream when the original TextIOWrapper is GC'd, causing:
    #   ValueError: I/O operation on closed file
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        # Python 3.7+: safe in-place reconfigure (does not replace/close stdout).
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import math
import time
import json
import logging
import asyncio
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from collections import deque
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _env_bool_optional(name: str) -> Optional[bool]:
    raw = os.getenv(name)
    if raw is None:
        return None
    return str(raw).strip().lower() in ("1", "true", "yes", "on")

# ═══════════════════════════════════════════════════════════════════════════
# ⚡🧬 HIGH FREQUENCY TRADING - HARMONIC MYCELIUM ENGINE
# ═══════════════════════════════════════════════════════════════════════════

try:
    from aureon.harmonic.aureon_hft_harmonic_mycelium import get_hft_engine, HFTTick
    HFT_ENGINE_AVAILABLE = True
except ImportError as e:
    HFT_ENGINE_AVAILABLE = False
    get_hft_engine = None
    HFTTick = None
    print(f"⚠️ HFT Engine not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 🌍 SACRED CONSTANTS & THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # 1.618 - Golden ratio threshold
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528

# Default cost thresholds (Tier 1 - 25bps taker)
DEFAULT_ROUND_TRIP_COST_PCT = 0.50  # Conservative: 2 × 25bps = 0.50%
DEFAULT_TIER_1_THRESHOLD = 0.60    # > 0.6% in 1 min = HOT
DEFAULT_TIER_2_THRESHOLD = 0.50    # > 0.5% in 5 min = STRONG
DEFAULT_TIER_3_THRESHOLD = 0.40    # > 0.4% in 5 min = VALID


# ═══════════════════════════════════════════════════════════════════════════
# 📊 DYNAMIC FEE-AWARE COST CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DynamicCostThresholds:
    """
    Cost thresholds that adjust based on actual fee tier.
    
    Formula: threshold = base_threshold × (fee_multiplier + spread_buffer)
    
    Lower tiers = higher fees = need bigger moves
    Higher tiers = lower fees = can catch smaller moves
    """
    tier: int
    maker_bps: int
    taker_bps: int
    spread_buffer_pct: float = 0.05  # 5bps buffer for spread
    
    # Computed thresholds
    round_trip_cost_pct: float = field(init=False)
    tier_1_hot_threshold: float = field(init=False)
    tier_2_strong_threshold: float = field(init=False)
    tier_3_valid_threshold: float = field(init=False)
    
    def __post_init__(self):
        # Round trip = 2 × taker fee (market orders both sides)
        self.round_trip_cost_pct = (self.taker_bps * 2) / 100 + self.spread_buffer_pct
        
        # Thresholds scale with cost (need move > cost to profit)
        # Tier 1 (HOT): Need 1.5× cost for safety margin
        self.tier_1_hot_threshold = self.round_trip_cost_pct * 1.5
        
        # Tier 2 (STRONG): Need 1.25× cost
        self.tier_2_strong_threshold = self.round_trip_cost_pct * 1.25
        
        # Tier 3 (VALID): Need to at least cover cost
        self.tier_3_valid_threshold = self.round_trip_cost_pct * 1.0
    
    def is_profitable_move(self, move_pct: float) -> Tuple[bool, str]:
        """Check if a move is profitable after costs."""
        if move_pct >= self.tier_1_hot_threshold:
            return True, "HOT"
        elif move_pct >= self.tier_2_strong_threshold:
            return True, "STRONG"
        elif move_pct >= self.tier_3_valid_threshold:
            return True, "VALID"
        else:
            return False, "BELOW_COST"
    
    def net_profit_pct(self, move_pct: float) -> float:
        """Calculate net profit after round-trip costs."""
        return move_pct - self.round_trip_cost_pct


# Fee tier presets (from alpaca_fee_tracker.py)
FEE_TIER_THRESHOLDS = {
    1: DynamicCostThresholds(tier=1, maker_bps=15, taker_bps=25),
    2: DynamicCostThresholds(tier=2, maker_bps=12, taker_bps=22),
    3: DynamicCostThresholds(tier=3, maker_bps=10, taker_bps=20),
    4: DynamicCostThresholds(tier=4, maker_bps=8, taker_bps=18),
    5: DynamicCostThresholds(tier=5, maker_bps=5, taker_bps=15),
    6: DynamicCostThresholds(tier=6, maker_bps=2, taker_bps=13),
    7: DynamicCostThresholds(tier=7, maker_bps=2, taker_bps=12),
    8: DynamicCostThresholds(tier=8, maker_bps=0, taker_bps=10),
}


# ═══════════════════════════════════════════════════════════════════════════
# 📡 SSE STREAMING TICKER CACHE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SSETickerData:
    """Real-time ticker data from SSE stream."""
    symbol: str
    price: float
    bid: float = 0.0
    ask: float = 0.0
    spread_pct: float = 0.0
    volume: float = 0.0
    change_1m: float = 0.0
    change_5m: float = 0.0
    change_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    timestamp: float = 0.0
    trade_count: int = 0
    vwap: float = 0.0
    is_stale: bool = False
    
    def age_seconds(self) -> float:
        """How old is this ticker data."""
        return time.time() - self.timestamp if self.timestamp > 0 else float('inf')


@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop on executed positions."""
    enabled: bool = True
    trail_percent: float = 2.0  # 2% trailing stop
    activation_profit_pct: float = 0.5  # Activate after 0.5% profit
    min_trail_pct: float = 0.5  # Minimum 0.5% trail
    max_trail_pct: float = 5.0  # Maximum 5% trail
    
    def calculate_trail(self, profit_pct: float) -> float:
        """
        Dynamic trail calculation based on profit.
        More profit = wider trail to let winners run.
        """
        if profit_pct <= 0:
            return self.trail_percent
        
        # Scale trail with profit (diminishing returns)
        # 0.5% profit = 2% trail
        # 2% profit = 2.5% trail  
        # 5% profit = 3% trail
        dynamic_trail = self.trail_percent + (math.log(1 + profit_pct) * 0.5)
        return max(self.min_trail_pct, min(self.max_trail_pct, dynamic_trail))


# ═══════════════════════════════════════════════════════════════════════════
# 🦙 ALPACA SCANNER BRIDGE - MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════

class AlpacaScannerBridge:
    """
    Unified bridge connecting Alpaca APIs to all scanner systems.
    
    Provides:
    1. SSE streaming integration for real-time tickers
    2. Dynamic fee-tier cost thresholds
    3. Trailing stop execution on 4th-pass trades
    4. Stock universe expansion (10K+ symbols)
    5. Binance→Alpaca execution bridge
    
    Usage:
        bridge = AlpacaScannerBridge(alpaca_client)
        bridge.start_streaming(['BTC/USD', 'ETH/USD'])
        
        # Get real-time ticker for scanner
        ticker = bridge.get_ticker('BTC/USD')
        
        # Check if move is profitable
        is_profitable, tier = bridge.is_move_profitable(0.3)
        
        # Execute with trailing stop
        bridge.execute_with_trailing_stop('BTC/USD', 'buy', 0.01)
    """
    
    def __init__(
        self,
        alpaca_client=None,
        fee_tracker=None,
        enable_sse: bool = True,
        enable_stocks: Optional[bool] = None,
        stock_filter: str = "sp500",  # "sp500", "nasdaq100", "all", "high_volume"
    ):
        self.alpaca = alpaca_client
        self.fee_tracker = fee_tracker
        self.enable_sse = enable_sse
        # Allow runner scripts to force-enable/disable stock scanning regardless of
        # how this class is instantiated.
        forced_stocks = _env_bool_optional("AUREON_SCAN_ALPACA_STOCKS")
        if forced_stocks is None:
            forced_stocks = _env_bool_optional("ALPACA_INCLUDE_STOCKS")

        if forced_stocks is not None:
            enable_stocks = forced_stocks
        elif enable_stocks is None:
            enable_stocks = True
        self.enable_stocks = bool(enable_stocks)
        self.stock_filter = stock_filter
        
        # SSE client (lazy init)
        self._sse_client = None
        self._sse_thread = None
        self._streaming = False
        
        # Real-time ticker cache
        self._ticker_cache: Dict[str, SSETickerData] = {}
        self._ticker_lock = threading.RLock()
        self._ticker_history: Dict[str, deque] = {}  # For momentum calc
        self._history_size = 300  # 5 minutes of 1-second ticks
        
        # Price momentum tracking
        self._price_snapshots: Dict[str, deque] = {}  # (timestamp, price)
        self._snapshot_interval = 1.0  # Seconds between snapshots
        
        # Dynamic cost thresholds
        self._cost_thresholds: DynamicCostThresholds = FEE_TIER_THRESHOLDS[1]
        self._last_tier_update: float = 0.0
        self._tier_update_interval: float = 3600  # 1 hour
        
        # Trailing stop management
        self._trailing_stops: Dict[str, Dict] = {}  # symbol -> stop config
        self._trailing_stop_config = TrailingStopConfig()
        
        # Stock universe (if enabled)
        self._stock_universe: Set[str] = set()
        self._crypto_universe: Set[str] = set()
        
        # Callbacks for scanner integration
        self._on_ticker_update: Optional[Callable] = None
        self._on_opportunity_detected: Optional[Callable] = None
        self._on_trailing_stop_triggered: Optional[Callable] = None
        
        # Statistics
        self._stats = {
            'tickers_received': 0,
            'opportunities_detected': 0,
            'trailing_stops_triggered': 0,
            'api_calls': 0,
            'sse_reconnects': 0,
            'start_time': None,
        }
        
        # Volume tracking (from fee tracker)
        self._current_volume_30d: float = 0.0
        
        # HFT Engine (lazy init)
        self.hft_engine = None
        
        logger.info("🦙🌊 Alpaca Scanner Bridge initialized")
        logger.info(f"   📡 SSE Streaming: {'ENABLED' if enable_sse else 'DISABLED'}")
        logger.info(f"   📈 Stock Scanning: {'ENABLED' if self.enable_stocks else 'DISABLED'}")
        # ASCII mirror lines for terminals/log sinks that drop emoji glyphs.
        logger.info("Alpaca Scanner Bridge initialized")
        logger.info(f"    SSE Streaming: {'ENABLED' if enable_sse else 'DISABLED'}")
        logger.info(f"    Stock Scanning: {'ENABLED' if self.enable_stocks else 'DISABLED'}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📡 SSE STREAMING INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def _get_sse_client(self):
        """Lazy initialization of SSE client."""
        if self._sse_client is None:
            try:
                from aureon.exchanges.alpaca_sse_client import AlpacaSSEClient
                self._sse_client = AlpacaSSEClient()
                
                # Wire callbacks
                self._sse_client.on_trade = self._on_sse_trade
                self._sse_client.on_quote = self._on_sse_quote
                self._sse_client.on_bar = self._on_sse_bar
                
                logger.info("   📡 SSE Client initialized")
            except ImportError:
                logger.warning("   ⚠️ alpaca_sse_client not available, using REST fallback")
        
        return self._sse_client
    
    def start_streaming(self, crypto_symbols: List[str] = None, stock_symbols: List[str] = None):
        """
        Start SSE streaming for real-time data.
        
        Args:
            crypto_symbols: List of crypto pairs (e.g., ['BTC/USD', 'ETH/USD'])
            stock_symbols: List of stock symbols (e.g., ['AAPL', 'MSFT'])
        """
        if not self.enable_sse:
            logger.info("   📡 SSE disabled, using REST polling")
            return False
        
        client = self._get_sse_client()
        if not client:
            return False
        
        self._streaming = True
        self._stats['start_time'] = time.time()
        
        # Start crypto stream
        if crypto_symbols:
            self._crypto_universe = set(crypto_symbols)
            client.start_crypto_stream(crypto_symbols, trades=True, quotes=True, bars=True)
            logger.info(f"   📡 Crypto streaming: {len(crypto_symbols)} symbols")
        
        # Start stock stream (if enabled)
        if stock_symbols and self.enable_stocks:
            self._stock_universe = set(stock_symbols)
            client.start_stock_stream(stock_symbols, trades=True, quotes=True)
            logger.info(f"   📈 Stock streaming: {len(stock_symbols)} symbols")
        
        # Start momentum calculation thread
        self._start_momentum_thread()
        
        return True
    
    def stop_streaming(self):
        """Stop all SSE streams."""
        self._streaming = False
        if self._sse_client:
            self._sse_client.stop()
        logger.info("   📡 Streaming stopped")
    
    def _on_sse_trade(self, trade):
        """Handle SSE trade event."""
        try:
            symbol = trade.symbol
            price = trade.price
            
            with self._ticker_lock:
                if symbol not in self._ticker_cache:
                    self._ticker_cache[symbol] = SSETickerData(symbol=symbol, price=price)
                
                ticker = self._ticker_cache[symbol]
                ticker.price = price
                ticker.timestamp = time.time()
                ticker.trade_count += 1
                ticker.is_stale = False
                
                # Track price history for momentum
                if symbol not in self._price_snapshots:
                    self._price_snapshots[symbol] = deque(maxlen=self._history_size)
                self._price_snapshots[symbol].append((time.time(), price))
            
            self._stats['tickers_received'] += 1
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # ⚡🧬 CONVERT SSE TRADE TO HFT TICK - SUB-10MS LATENCY
            # ═══════════════════════════════════════════════════════════════════════════════
            if HFT_ENGINE_AVAILABLE and HFTTick:
                try:
                    # Lazy initialize HFT engine
                    if self.hft_engine is None:
                        self.hft_engine = get_hft_engine()
                        if self.hft_engine:
                            logger.info("   ⚡🧬 HFT Engine wired to Alpaca SSE Bridge")
                    
                    # Create HFT tick from SSE trade
                    if self.hft_engine:
                        hft_tick = HFTTick(
                            symbol=symbol,
                            price=price,
                            volume=trade.size,
                            timestamp=trade.timestamp,
                            exchange="alpaca",
                            tick_type="trade",
                            bid_price=ticker.bid if ticker.bid > 0 else price * 0.9995,  # Estimate bid
                            ask_price=ticker.ask if ticker.ask > 0 else price * 1.0005,  # Estimate ask
                        )
                        
                        # Inject tick into HFT engine
                        self.hft_engine.inject_tick(hft_tick)
                        
                except Exception as e:
                    logger.debug(f"HFT tick injection error: {e}")
            
            # Fire callback
            if self._on_ticker_update:
                self._on_ticker_update(symbol, ticker)
                
        except Exception as e:
            logger.debug(f"SSE trade error: {e}")
    
    def _on_sse_quote(self, quote):
        """Handle SSE quote event."""
        try:
            symbol = quote.symbol
            
            with self._ticker_lock:
                if symbol not in self._ticker_cache:
                    mid = (quote.bid_price + quote.ask_price) / 2
                    self._ticker_cache[symbol] = SSETickerData(symbol=symbol, price=mid)
                
                ticker = self._ticker_cache[symbol]
                ticker.bid = quote.bid_price
                ticker.ask = quote.ask_price
                ticker.timestamp = time.time()
                
                if quote.bid_price > 0:
                    ticker.spread_pct = ((quote.ask_price - quote.bid_price) / quote.bid_price) * 100
                
                ticker.is_stale = False
                
        except Exception as e:
            logger.debug(f"SSE quote error: {e}")
    
    def _on_sse_bar(self, bar):
        """Handle SSE bar event."""
        try:
            symbol = bar.symbol
            
            with self._ticker_lock:
                if symbol not in self._ticker_cache:
                    self._ticker_cache[symbol] = SSETickerData(symbol=symbol, price=bar.close)
                
                ticker = self._ticker_cache[symbol]
                ticker.high_24h = max(ticker.high_24h, bar.high)
                ticker.low_24h = min(ticker.low_24h, bar.low) if ticker.low_24h > 0 else bar.low
                ticker.volume += bar.volume
                ticker.vwap = bar.vwap
                ticker.timestamp = time.time()
                ticker.is_stale = False
                
        except Exception as e:
            logger.debug(f"SSE bar error: {e}")
    
    def _start_momentum_thread(self):
        """Start background thread to calculate momentum."""
        def momentum_worker():
            while self._streaming:
                try:
                    self._calculate_all_momentum()
                    time.sleep(1.0)  # Calculate every second
                except Exception as e:
                    logger.debug(f"Momentum calc error: {e}")
        
        self._momentum_thread = threading.Thread(target=momentum_worker, daemon=True)
        self._momentum_thread.start()
    
    def _calculate_all_momentum(self):
        """Calculate momentum for all tracked symbols."""
        now = time.time()
        
        with self._ticker_lock:
            for symbol, snapshots in self._price_snapshots.items():
                if len(snapshots) < 2:
                    continue
                
                ticker = self._ticker_cache.get(symbol)
                if not ticker:
                    continue
                
                current_price = ticker.price
                
                # 1-minute change
                one_min_ago = now - 60
                for ts, price in reversed(snapshots):
                    if ts <= one_min_ago:
                        if price > 0:
                            ticker.change_1m = ((current_price - price) / price) * 100
                        break
                
                # 5-minute change
                five_min_ago = now - 300
                for ts, price in reversed(snapshots):
                    if ts <= five_min_ago:
                        if price > 0:
                            ticker.change_5m = ((current_price - price) / price) * 100
                        break
                
                # Check for opportunity
                self._check_opportunity(symbol, ticker)
    
    def _check_opportunity(self, symbol: str, ticker: SSETickerData):
        """Check if ticker represents a profitable opportunity."""
        # Check 1-minute move
        is_profitable_1m, tier_1m = self._cost_thresholds.is_profitable_move(abs(ticker.change_1m))
        
        if is_profitable_1m and tier_1m == "HOT":
            self._stats['opportunities_detected'] += 1
            
            if self._on_opportunity_detected:
                self._on_opportunity_detected({
                    'symbol': symbol,
                    'price': ticker.price,
                    'change_1m': ticker.change_1m,
                    'change_5m': ticker.change_5m,
                    'tier': tier_1m,
                    'net_profit_pct': self._cost_thresholds.net_profit_pct(abs(ticker.change_1m)),
                    'timestamp': time.time(),
                })
    
    # ═══════════════════════════════════════════════════════════════════════
    # 💰 DYNAMIC FEE TIER MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def update_fee_tier(self, force: bool = False) -> DynamicCostThresholds:
        """
        Update cost thresholds based on current fee tier.
        
        Queries AlpacaFeeTracker for actual 30-day volume and tier.
        """
        now = time.time()
        
        # Check if update needed
        if not force and (now - self._last_tier_update) < self._tier_update_interval:
            return self._cost_thresholds
        
        self._last_tier_update = now
        
        # Get tier from fee tracker
        tier_num = 1  # Default
        
        if self.fee_tracker:
            try:
                tier_info = self.fee_tracker.get_fee_tier()
                tier_num = tier_info.tier
                self._current_volume_30d = getattr(self.fee_tracker, 'volume_30d', 0.0)
                logger.info(f"💰 Fee tier updated: Tier {tier_num} (30d vol: ${self._current_volume_30d:,.2f})")
            except Exception as e:
                logger.warning(f"⚠️ Could not get fee tier: {e}")
        
        # Update thresholds
        self._cost_thresholds = FEE_TIER_THRESHOLDS.get(tier_num, FEE_TIER_THRESHOLDS[1])
        
        logger.info(f"   📊 Cost Thresholds Updated:")
        logger.info(f"      Round-trip: {self._cost_thresholds.round_trip_cost_pct:.3f}%")
        logger.info(f"      HOT (1m): >{self._cost_thresholds.tier_1_hot_threshold:.3f}%")
        logger.info(f"      STRONG (5m): >{self._cost_thresholds.tier_2_strong_threshold:.3f}%")
        logger.info(f"      VALID: >{self._cost_thresholds.tier_3_valid_threshold:.3f}%")
        
        return self._cost_thresholds
    
    @property
    def current_volume_30d(self) -> float:
        """Get current 30-day trading volume."""
        return self._current_volume_30d
        
        return self._cost_thresholds
    
    def get_cost_thresholds(self) -> DynamicCostThresholds:
        """Get current cost thresholds."""
        return self._cost_thresholds
    
    def is_move_profitable(self, move_pct: float) -> Tuple[bool, str]:
        """Check if a price move is profitable after costs."""
        return self._cost_thresholds.is_profitable_move(abs(move_pct))
    
    def calculate_net_profit(self, move_pct: float) -> float:
        """Calculate net profit after round-trip costs."""
        return self._cost_thresholds.net_profit_pct(abs(move_pct))
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📈 TRAILING STOP EXECUTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def execute_with_trailing_stop(
        self,
        symbol: str,
        side: str,
        qty: float,
        trail_percent: float = None,
    ) -> Optional[Dict]:
        """
        Execute trade and set up trailing stop for profit protection.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            qty: Quantity
            trail_percent: Custom trail %, or use config default
            
        Returns:
            Order result with trailing stop details
        """
        if not self.alpaca:
            logger.error("❌ Alpaca client not configured")
            return None
        
        try:
            # Execute main order
            logger.info(f"🎯 Executing {side} {qty} {symbol}")
            
            result = self.alpaca.place_market_order(symbol, side, qty)
            
            if not result or result.get('status') == 'error':
                logger.error(f"❌ Order failed: {result}")
                return result
            
            fill_price = float(result.get('filled_avg_price', 0) or 0)
            
            # Only set trailing stop for buys (we want to protect long positions)
            if side == 'buy' and self._trailing_stop_config.enabled:
                trail_pct = trail_percent or self._trailing_stop_config.trail_percent
                
                # Store trailing stop config
                self._trailing_stops[symbol] = {
                    'entry_price': fill_price,
                    'trail_percent': trail_pct,
                    'highest_price': fill_price,
                    'stop_price': fill_price * (1 - trail_pct / 100),
                    'qty': float(result.get('filled_qty', qty)),
                    'activated': False,
                    'created_at': time.time(),
                }
                
                logger.info(f"   🛡️ Trailing stop configured: {trail_pct}% (stop @ ${self._trailing_stops[symbol]['stop_price']:.2f})")
                
                result['trailing_stop'] = self._trailing_stops[symbol]
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Execute with trailing stop error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def place_trailing_stop_order(self, symbol: str, qty: float, trail_percent: float) -> Optional[Dict]:
        """
        Place a trailing stop order directly via Alpaca API.
        
        Uses Alpaca's native trailing stop order type.
        """
        if not self.alpaca:
            return None
        
        try:
            result = self.alpaca.place_trailing_stop_order(
                symbol=symbol,
                side='sell',
                qty=qty,
                trail_percent=trail_percent
            )
            
            logger.info(f"🛡️ Trailing stop order placed: {symbol} qty={qty} trail={trail_percent}%")
            return result
            
        except Exception as e:
            logger.error(f"❌ Trailing stop order error: {e}")
            return None
    
    def update_trailing_stops(self):
        """
        Update all trailing stops based on current prices.
        Called periodically from scanner loop.
        """
        with self._ticker_lock:
            for symbol, stop in list(self._trailing_stops.items()):
                ticker = self._ticker_cache.get(symbol)
                if not ticker:
                    continue
                
                current_price = ticker.price
                entry_price = stop['entry_price']
                
                # Calculate current profit
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Check if trailing stop should activate
                if not stop['activated'] and profit_pct >= self._trailing_stop_config.activation_profit_pct:
                    stop['activated'] = True
                    logger.info(f"🛡️ Trailing stop ACTIVATED for {symbol} at {profit_pct:.2f}% profit")
                
                # Update trailing stop if activated
                if stop['activated']:
                    if current_price > stop['highest_price']:
                        stop['highest_price'] = current_price
                        
                        # Dynamic trail calculation
                        trail_pct = self._trailing_stop_config.calculate_trail(profit_pct)
                        stop['trail_percent'] = trail_pct
                        stop['stop_price'] = current_price * (1 - trail_pct / 100)
                    
                    # Check if stop triggered
                    if current_price <= stop['stop_price']:
                        self._trigger_trailing_stop(symbol, stop, current_price)
    
    def _trigger_trailing_stop(self, symbol: str, stop: Dict, current_price: float):
        """Execute trailing stop - sell position."""
        logger.warning(f"🛑 TRAILING STOP TRIGGERED: {symbol} @ ${current_price:.2f}")
        
        try:
            # Execute sell
            if self.alpaca:
                result = self.alpaca.place_market_order(symbol, 'sell', stop['qty'])
                
                profit_usd = (current_price - stop['entry_price']) * stop['qty']
                logger.info(f"   💰 Position closed. Profit: ${profit_usd:.2f}")
            
            self._stats['trailing_stops_triggered'] += 1
            
            # Fire callback
            if self._on_trailing_stop_triggered:
                self._on_trailing_stop_triggered({
                    'symbol': symbol,
                    'entry_price': stop['entry_price'],
                    'exit_price': current_price,
                    'qty': stop['qty'],
                    'profit_pct': ((current_price - stop['entry_price']) / stop['entry_price']) * 100,
                })
            
            # Remove from tracking
            del self._trailing_stops[symbol]
            
        except Exception as e:
            logger.error(f"❌ Trailing stop execution failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 TICKER DATA FOR SCANNERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get ticker data for scanner consumption.
        
        Returns data in format expected by GlobalWaveScanner.
        """
        with self._ticker_lock:
            ticker = self._ticker_cache.get(symbol)
            
            if ticker and ticker.age_seconds() < 30:  # Fresh data
                return {
                    'symbol': symbol,
                    'price': ticker.price,
                    'lastPrice': ticker.price,
                    'change24h': ticker.change_24h,
                    'priceChangePercent': ticker.change_24h,
                    'change_1m': ticker.change_1m,
                    'change_5m': ticker.change_5m,
                    'volume': ticker.volume,
                    'quoteVolume': ticker.volume,
                    'high': ticker.high_24h,
                    'highPrice': ticker.high_24h,
                    'low': ticker.low_24h,
                    'lowPrice': ticker.low_24h,
                    'bid': ticker.bid,
                    'ask': ticker.ask,
                    'spread_pct': ticker.spread_pct,
                    'timestamp': ticker.timestamp,
                    'source': 'sse',
                }
        
        # Fallback to REST if no SSE data
        return self._fetch_ticker_rest(symbol)
    
    def get_all_tickers(self) -> Dict[str, Dict]:
        """Get all cached tickers for batch scanner access."""
        tickers = {}
        
        with self._ticker_lock:
            for symbol, ticker in self._ticker_cache.items():
                if ticker.age_seconds() < 60:  # Not too stale
                    tickers[symbol] = self.get_ticker(symbol)
        
        return tickers
    
    def _fetch_ticker_rest(self, symbol: str) -> Optional[Dict]:
        """Fallback: fetch ticker via REST API."""
        if not self.alpaca:
            return None
        
        try:
            self._stats['api_calls'] += 1
            
            # Get latest quote
            quotes = self.alpaca.get_latest_crypto_quotes([symbol])
            if symbol not in quotes:
                return None
            
            q = quotes[symbol]
            bid = float(q.get('bp', 0) or 0)
            ask = float(q.get('ap', 0) or 0)
            mid = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
            
            return {
                'symbol': symbol,
                'price': mid,
                'lastPrice': mid,
                'bid': bid,
                'ask': ask,
                'spread_pct': ((ask - bid) / bid * 100) if bid > 0 else 0,
                'timestamp': time.time(),
                'source': 'rest',
            }
            
        except Exception as e:
            logger.debug(f"REST ticker fetch error for {symbol}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📈 STOCK UNIVERSE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_stock_universe(self, filter_type: str = None) -> List[str]:
        """
        Get stock universe based on filter.
        
        Filters:
        - sp500: S&P 500 components
        - nasdaq100: NASDAQ 100
        - high_volume: Top 500 by volume
        - all: All active stocks (10K+)
        """
        if not self.alpaca:
            return []
        
        filter_type = filter_type or self.stock_filter
        
        try:
            # Get all active stocks
            assets = self.alpaca.list_assets(status='active', asset_class='us_equity')
            
            symbols = []
            for asset in assets:
                sym = asset.get('symbol') if isinstance(asset, dict) else getattr(asset, 'symbol', None)
                tradable = asset.get('tradable', True) if isinstance(asset, dict) else getattr(asset, 'tradable', True)
                
                if sym and tradable:
                    symbols.append(sym)
            
            logger.info(f"📈 Stock universe loaded: {len(symbols)} symbols")
            
            # Apply filter
            if filter_type == 'sp500':
                # Would need external data source for SP500 components
                # For now, return top symbols
                return symbols[:500]
            elif filter_type == 'nasdaq100':
                return symbols[:100]
            elif filter_type == 'high_volume':
                return symbols[:500]
            else:
                return symbols
            
        except Exception as e:
            logger.error(f"❌ Could not load stock universe: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════
    # 📊 STATISTICS & HEALTH
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """Get bridge statistics."""
        stats = self._stats.copy()
        
        if stats['start_time']:
            elapsed = time.time() - stats['start_time']
            stats['elapsed_seconds'] = elapsed
            stats['tickers_per_second'] = stats['tickers_received'] / elapsed if elapsed > 0 else 0
        
        stats['active_trailing_stops'] = len(self._trailing_stops)
        stats['cached_tickers'] = len(self._ticker_cache)
        stats['current_fee_tier'] = self._cost_thresholds.tier
        
        return stats
    
    def health_check(self) -> Dict:
        """Perform health check on all integrations."""
        health = {
            'sse_streaming': self._streaming,
            'sse_client_available': self._sse_client is not None,
            'alpaca_client_available': self.alpaca is not None,
            'fee_tracker_available': self.fee_tracker is not None,
            'cached_ticker_count': len(self._ticker_cache),
            'trailing_stops_active': len(self._trailing_stops),
            'cost_threshold_tier': self._cost_thresholds.tier,
            'status': 'healthy',
        }
        
        # Check for issues
        if not self.alpaca:
            health['status'] = 'degraded'
            health['issue'] = 'No Alpaca client'
        elif self._streaming and len(self._ticker_cache) == 0:
            health['status'] = 'warning'
            health['issue'] = 'Streaming enabled but no tickers received'
        
        return health
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🔗 CALLBACK REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def on_ticker_update(self, callback: Callable):
        """Register callback for ticker updates."""
        self._on_ticker_update = callback
    
    def on_opportunity_detected(self, callback: Callable):
        """Register callback for profitable opportunities."""
        self._on_opportunity_detected = callback
    
    def on_trailing_stop_triggered(self, callback: Callable):
        """Register callback for trailing stop triggers."""
        self._on_trailing_stop_triggered = callback


# ═══════════════════════════════════════════════════════════════════════════
# 🏭 FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def create_scanner_bridge(
    enable_sse: bool = True,
    enable_stocks: bool = False,
) -> AlpacaScannerBridge:
    """
    Factory function to create scanner bridge with all integrations.
    
    Automatically wires:
    - AlpacaClient
    - AlpacaFeeTracker
    - SSE streaming (if enabled)
    """
    alpaca_client = None
    fee_tracker = None
    
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
        alpaca_client = AlpacaClient()
        logger.info("🦙 AlpacaClient loaded")
    except Exception as e:
        logger.warning(f"⚠️ Could not load AlpacaClient: {e}")
    
    try:
        from aureon.exchanges.alpaca_fee_tracker import AlpacaFeeTracker
        fee_tracker = AlpacaFeeTracker(alpaca_client)
        logger.info("💰 AlpacaFeeTracker loaded")
    except Exception as e:
        logger.warning(f"⚠️ Could not load AlpacaFeeTracker: {e}")
    
    bridge = AlpacaScannerBridge(
        alpaca_client=alpaca_client,
        fee_tracker=fee_tracker,
        enable_sse=enable_sse,
        enable_stocks=enable_stocks,
    )
    
    # Update fee tier immediately
    bridge.update_fee_tier(force=True)
    
    return bridge


# ═══════════════════════════════════════════════════════════════════════════
# 🎬 DEMO & CLI
# ═══════════════════════════════════════════════════════════════════════════

def demo_scanner_bridge():
    """Demo the scanner bridge functionality."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🦙🌊 ALPACA SCANNER BRIDGE DEMO 🌊🦙                                             ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Create bridge
    bridge = create_scanner_bridge(enable_sse=True, enable_stocks=False)
    
    # Register callbacks
    def on_opportunity(opp: Dict):
        print(f"  🎯 OPPORTUNITY: {opp['symbol']} {opp['change_1m']:+.2f}% → Net: {opp['net_profit_pct']:.3f}%")
    
    bridge.on_opportunity_detected(on_opportunity)
    
    # Show thresholds
    thresholds = bridge.get_cost_thresholds()
    print(f"\n📊 Cost Thresholds (Tier {thresholds.tier}):")
    print(f"   Round-trip cost: {thresholds.round_trip_cost_pct:.3f}%")
    print(f"   HOT threshold: >{thresholds.tier_1_hot_threshold:.3f}%")
    print(f"   STRONG threshold: >{thresholds.tier_2_strong_threshold:.3f}%")
    print(f"   VALID threshold: >{thresholds.tier_3_valid_threshold:.3f}%")
    
    # Start streaming
    print(f"\n📡 Starting SSE stream for BTC, ETH, SOL...")
    crypto_symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'AVAX/USD']
    bridge.start_streaming(crypto_symbols=crypto_symbols)
    
    print("\n🌊 Scanning for 60 seconds...")
    print("-" * 60)
    
    try:
        for i in range(60):
            time.sleep(1)
            
            # Update trailing stops
            bridge.update_trailing_stops()
            
            # Show progress every 10 seconds
            if (i + 1) % 10 == 0:
                stats = bridge.get_stats()
                print(f"  [{i+1}s] Tickers: {stats['tickers_received']} | Opps: {stats['opportunities_detected']}")
    except KeyboardInterrupt:
        pass
    
    # Show final stats
    bridge.stop_streaming()
    
    print("\n" + "=" * 60)
    stats = bridge.get_stats()
    print(f"📊 Final Statistics:")
    print(f"   Tickers received: {stats['tickers_received']}")
    print(f"   Opportunities detected: {stats['opportunities_detected']}")
    print(f"   API calls (REST fallback): {stats['api_calls']}")
    print(f"   Current fee tier: {stats['current_fee_tier']}")
    
    health = bridge.health_check()
    print(f"\n🏥 Health Check: {health['status'].upper()}")
    
    print("\n✅ Demo complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    demo_scanner_bridge()
