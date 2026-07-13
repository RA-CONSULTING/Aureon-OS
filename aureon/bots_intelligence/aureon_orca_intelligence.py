#!/usr/bin/env python3
"""
🦈→🐋→🔪 ORCA KILLER WHALE INTELLIGENCE 🔪🐋←🦈
================================================

THE KILLER WHALE HUNTS WHALES.

We don't just watch the market - WE PROFIT FROM IT.
This module connects ALL the intelligence we're collecting to ACTUAL TRADES.

STRATEGY: "Whale Wake Riding"
1. DETECT: Whale makes a big move (we see it via whale_alerts, firm_attribution)
2. ANALYZE: What direction? Who's behind it? (firm_attribution, market_thesis)
3. HARMONIZE: Is the timing right? (harmonic resonance, Schumann, phi alignment)
4. RIDE: Jump on the wake and ride it for micro-profits
5. EXIT: Get out before the wave crashes (coherence drop detection)

KILLER WHALE RULES:
- We're faster than whales (react in milliseconds)
- We ride THEIR momentum, not fight it
- Take small bites - lots of them
- Exit before they turn on us
- Never fight Citadel head-on, ride behind them

Gary Leckey | January 2026 | ORCA MODE ACTIVATED
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import math
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

# UTF-8 fix for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping - causes Windows exit errors
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - kHz-Speed Whale Hunting Signals
# ═══════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection, ChirpType
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# 📡 THOUGHT BUS INTEGRATION - Neural Persistence
THOUGHT_BUS_AVAILABLE = False
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# Counter-intelligence integration
try:
    from aureon.utils.aureon_queen_counter_intelligence import (
        queen_counter_intelligence,
        CounterIntelligenceSignal,
        CounterStrategy
    )
    from aureon.bots_intelligence.aureon_global_firm_intelligence import get_attribution_engine
    from aureon.bots_intelligence.firm_name_matcher import match_firm_name_simple, match_firm_name
    COUNTER_INTEL_AVAILABLE = True
except ImportError:
    COUNTER_INTEL_AVAILABLE = False
    queen_counter_intelligence = None
    get_attribution_engine = None
    match_firm_name_simple = None
    match_firm_name = None

# 💰👁️ REAL PORTFOLIO TRACKER - NO PHANTOM NUMBERS! 👁️💰
try:
    from aureon.portfolio.aureon_real_portfolio_tracker import (
        RealPortfolioTracker,
        get_real_portfolio_tracker,
        get_real_balance,
        RealPortfolioSnapshot
    )
    REAL_PORTFOLIO_AVAILABLE = True
except ImportError:
    RealPortfolioTracker = None
    get_real_portfolio_tracker = None
    get_real_balance = None
    RealPortfolioSnapshot = None
    REAL_PORTFOLIO_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 GLOBAL MARKET INTEGRATION - Full Exchange Coverage
# ═══════════════════════════════════════════════════════════════════════════════
# Kraken (crypto)
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

# Binance (REST + WebSocket)
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None

try:
    from aureon.exchanges.binance_ws_client import BinanceWebSocketClient
    BINANCE_WS_AVAILABLE = True
except ImportError:
    BINANCE_WS_AVAILABLE = False
    BinanceWebSocketClient = None

# Alpaca (stocks + crypto)
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

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

# Movers & Shakers Scanner (unified whale detection)
try:
    from aureon.scanners.aureon_movers_shakers_scanner import (
        MoversShakersScanner, MoverShaker, WaveReport, WaveType
    )
    MOVERS_SHAKERS_AVAILABLE = True
except ImportError:
    MOVERS_SHAKERS_AVAILABLE = False
    MoversShakersScanner = None
    MoverShaker = None
    WaveReport = None
    WaveType = None

# Moby Dick Whale Hunter (legendary strategies)
try:
    from aureon.analytics.aureon_moby_dick_whale_hunter import MobyDickWhaleHunter
    MOBY_DICK_AVAILABLE = True
except ImportError:
    MOBY_DICK_AVAILABLE = False
    MobyDickWhaleHunter = None

# Sacred constants for harmonic timing
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio 1.618
PHI_INVERSE = 0.618  # φ⁻¹ - The trigger threshold
SCHUMANN_BASE = 7.83  # Hz - Earth's heartbeat
LOVE_FREQUENCY = 528  # Hz - DNA repair frequency


@dataclass
class WhaleSignal:
    """A detected whale movement with trading implications."""
    timestamp: float
    symbol: str
    side: str  # 'buy' or 'sell'
    volume_usd: float
    firm: Optional[str] = None
    firm_confidence: float = 0.0
    exchange: str = "unknown"
    
    # Derived trading signals
    momentum_direction: str = "neutral"  # 'bullish', 'bearish', 'neutral'
    ride_confidence: float = 0.0  # How confident are we to ride this wake?
    suggested_action: str = "hold"  # 'buy', 'sell', 'hold'
    target_pnl_pct: float = 0.001  # 0.1% default target


@dataclass
class HarmonicTiming:
    """Harmonic resonance data for timing trades."""
    schumann_alignment: float = 0.5
    phi_alignment: float = 0.5
    love_alignment: float = 0.5
    coherence: float = 0.5
    
    def is_favorable(self) -> bool:
        """Check if harmonics favor trading."""
        return self.coherence >= PHI_INVERSE  # 0.618 threshold
    
    def timing_multiplier(self) -> float:
        """Get a timing multiplier for position sizing."""
        # Higher coherence = more confidence = larger position
        return 0.5 + (self.coherence * 0.5)  # Range: 0.5 to 1.0


@dataclass 
class OrcaOpportunity:
    """A trading opportunity identified by the Orca Intelligence."""
    id: str
    timestamp: float
    symbol: str
    action: str  # 'buy' or 'sell'
    
    # Source signals
    whale_signal: Optional[WhaleSignal] = None
    firm_attribution: Optional[str] = None
    market_thesis: Optional[str] = None
    
    # Confidence & sizing
    confidence: float = 0.0
    harmonic_timing: Optional[HarmonicTiming] = None
    position_size_pct: float = 0.01  # 1% of available capital
    
    # Entry conditions
    entry_price: float = 0.0
    entry_timestamp: float = 0.0
    
    # Risk management - ENHANCED FOR CLEAN KILLS
    target_pnl_usd: float = 0.10  # $0.10 minimum profit target
    max_hold_seconds: int = 300  # 5 minutes max hold
    stop_loss_pct: float = 0.005  # 0.5% stop loss
    
    # Dynamic exit conditions - NEW CLEAN KILL MATH
    trailing_stop_pct: float = 0.002  # 0.2% trailing stop
    partial_exit_pct: float = 0.5  # Exit 50% at first target
    partial_target_mult: float = 1.5  # 1.5x target for partial exit
    whale_reversal_threshold: float = 0.7  # Exit if whale momentum reverses 70%
    harmonic_decay_threshold: float = 0.3  # Exit if coherence drops below 30%
    profit_lock_pct: float = 0.01  # Lock in profit at 1% gain
    
    # Exit tracking
    highest_price: float = 0.0  # For trailing stops
    lowest_price: float = float('inf')  # For trailing stops
    partial_exited: bool = False
    trailing_stop_price: float = 0.0
    
    # Reasoning chain
    reasoning: List[str] = field(default_factory=list)
    
    def update_price(self, current_price: float) -> None:
        """Update price tracking for dynamic exits."""
        if self.action == 'buy':
            self.highest_price = max(self.highest_price, current_price)
            # Update trailing stop for longs
            if self.highest_price > self.entry_price:
                profit_pct = (self.highest_price - self.entry_price) / self.entry_price
                if profit_pct >= self.profit_lock_pct:
                    # Lock in profit with trailing stop
                    self.trailing_stop_price = self.highest_price * (1 - self.trailing_stop_pct)
        else:  # sell/short
            self.lowest_price = min(self.lowest_price, current_price)
            # Update trailing stop for shorts
            if self.lowest_price < self.entry_price:
                profit_pct = (self.entry_price - self.lowest_price) / self.entry_price
                if profit_pct >= self.profit_lock_pct:
                    # Lock in profit with trailing stop
                    self.trailing_stop_price = self.lowest_price * (1 + self.trailing_stop_pct)
    
    def should_exit(self, current_price: float, orca_intelligence) -> Tuple[bool, str]:
        """
        ENHANCED EXIT LOGIC - CLEAN KILLS ONLY!
        Returns (should_exit, reason)
        """
        if not self.entry_price:
            return False, "No entry price set"
        
        time_held = time.time() - self.entry_price
        price_change_pct = (current_price - self.entry_price) / self.entry_price
        
        # 1. TIME-BASED EXITS
        if time_held > self.max_hold_seconds:
            return True, f"Max hold time exceeded ({self.max_hold_seconds}s)"
        
        # 2. STOP LOSS - HARD FLOOR
        if self.action == 'buy' and price_change_pct <= -self.stop_loss_pct:
            return True, f"Stop loss hit: {price_change_pct:.2%}"
        elif self.action == 'sell' and price_change_pct >= self.stop_loss_pct:
            return True, f"Stop loss hit: {price_change_pct:.2%}"
        
        # 3. TRAILING STOP - LOCK IN PROFITS
        if self.trailing_stop_price > 0:
            if self.action == 'buy' and current_price <= self.trailing_stop_price:
                return True, f"Trailing stop hit at ${self.trailing_stop_price:.4f}"
            elif self.action == 'sell' and current_price >= self.trailing_stop_price:
                return True, f"Trailing stop hit at ${self.trailing_stop_price:.4f}"
        
        # 4. PARTIAL EXIT AT FIRST TARGET
        if not self.partial_exited:
            target_hit = False
            if self.action == 'buy':
                target_hit = current_price >= self.entry_price * (1 + self.target_pnl_usd / (self.entry_price * self.partial_target_mult))
            else:
                target_hit = current_price <= self.entry_price * (1 - self.target_pnl_usd / (self.entry_price * self.partial_target_mult))
            
            if target_hit:
                self.partial_exited = True
                return True, f"Partial exit at {self.partial_target_mult}x target"
        
        # 5. WHALE MOMENTUM REVERSAL
        momentum = orca_intelligence.symbol_momentum.get(self.symbol, 0.0)
        if self.action == 'buy' and momentum <= -self.whale_reversal_threshold:
            return True, f"Whale momentum reversed: {momentum:.2f}"
        elif self.action == 'sell' and momentum >= self.whale_reversal_threshold:
            return True, f"Whale momentum reversed: {momentum:.2f}"
        
        # 6. HARMONIC DECAY
        if orca_intelligence.harmonic_data:
            coherence = orca_intelligence.harmonic_data.coherence
            if coherence < self.harmonic_decay_threshold:
                return True, f"Harmonic coherence decayed: {coherence:.2%}"
        
        # 7. PROFIT TARGET ACHIEVED
        pnl_usd = abs(price_change_pct) * self.entry_price
        if pnl_usd >= self.target_pnl_usd:
            return True, f"Profit target achieved: ${pnl_usd:.4f}"
        
        return False, "Hold position"
    
    def calculate_exit_size(self, current_price: float) -> float:
        """Calculate position size to exit (partial or full)."""
        if not self.partial_exited:
            # First exit - partial
            return self.partial_exit_pct
        else:
            # Second exit - remaining position
            return 1.0
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'position_size_pct': self.position_size_pct,
            'target_pnl_usd': self.target_pnl_usd,
            'entry_price': self.entry_price,
            'trailing_stop_price': self.trailing_stop_price,
            'partial_exited': self.partial_exited,
            'reasoning': self.reasoning
        }


class OrcaKillerWhaleIntelligence:
    """
    🦈🔪 THE KILLER WHALE 🔪🦈
    
    COMMAND HIERARCHY: 👑 QUEEN → 🦈 ORCA → 💰 MICRO PROFIT
    ═══════════════════════════════════════════════════════════════
    
    Position in Hierarchy: TACTICAL COMMANDER (Level 2)
    
    Reports to: 👑 Queen Sero (Supreme Commander)
    Commands:  💰 Micro Profit Engine (Executor)
    
    Responsibilities:
    - Hunt whales and identify opportunities
    - Request Queen approval for high-value hunts
    - Coordinate with Micro Profit for execution
    - Report outcomes back up the chain
    
    The Queen has VETO POWER over all Orca decisions.
    The Orca has COMMAND AUTHORITY over Micro Profit execution.
    
    Connects ALL intelligence streams to generate trading signals.
    We hunt whales and ride their wakes for profit.
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HIERARCHY CONSTANTS
    # ═══════════════════════════════════════════════════════════════════════════
    HIERARCHY_LEVEL = 2  # Queen=1, Orca=2, MicroProfit=3
    HIERARCHY_NAME = "TACTICAL_COMMANDER"
    REPORTS_TO = "QUEEN_SERO"
    COMMANDS = ["MICRO_PROFIT_ENGINE"]
    
    # Thresholds for Queen consultation
    QUEEN_CONSULT_THRESHOLD_USD = 5.0   # Consult Queen for trades > $5
    QUEEN_CONSULT_CONFIDENCE = 0.7      # Consult if confidence < 70%
    QUEEN_VETO_OVERRIDE = False         # Queen veto CANNOT be overridden
    
    # Risk/quality gates
    MIN_OPPORTUNITY_CONFIDENCE = 0.30
    MIN_TARGET_PNL_USD = 0.10
    MAX_POSITION_SIZE_PCT = 0.03
    MAX_TOTAL_EXPOSURE_PCT = 0.06
    MAX_SYMBOL_EXPOSURE_PCT = 0.03
    STALE_PRICE_SECONDS = 15
    BANNED_SYMBOL_TOKENS = ("PUMP", "MOON", "INU", "PEPE")
    DEFAULT_ALLOWED_QUOTES = ("USD", "USDT", "USDC")
    
    def __init__(self):
        self.enabled = True
        self.mode = "STALKING"  # STALKING, HUNTING, FEEDING, RESTING
        
        # � COMMUNICATION BUSES
        try:
            self.thought_bus = ThoughtBus()
            self.chirp_bus = get_chirp_bus() if CHIRP_BUS_AVAILABLE and get_chirp_bus else None
            print("✅ ORCA: Connected to ThoughtBus and ChirpBus")
        except Exception as e:
            print(f"⚠️ ORCA: Bus connection failed: {e}")
            self.thought_bus = None
            self.chirp_bus = None

        # �👑 QUEEN REFERENCE - Supreme Commander
        self.queen = None  # Will be wired externally
        self.queen_connected = False
        self.queen_consultation_count = 0
        self.queen_approvals = 0
        self.queen_vetoes = 0
        
        # 💰 MICRO PROFIT REFERENCE - Executor
        self.micro_profit = None  # Will be wired externally
        self.micro_profit_connected = False
        self.execution_orders_sent = 0
        self.execution_orders_completed = 0
        
        # ⚡ HFT ENGINE REFERENCE - High-frequency execution
        self.hft_engine = None  # Will be wired externally
        self.hft_connected = False
        
        # 🌐 GLOBAL MARKET VISIBILITY - Connect to ALL exchanges and feeds
        self.kraken_client = None
        self.binance_client = None
        self.binance_ws = None
        self.alpaca_client = None
        self.capital_client = None
        self.wave_scanner = None
        self._init_market_connections()
        
        # Intelligence feeds (connected externally)
        self.whale_signals: deque = deque(maxlen=100)
        self.firm_activity: Dict[str, Dict] = {}
        self.market_thesis: Optional[Dict] = None
        self.harmonic_data: Optional[HarmonicTiming] = None
        self.fear_greed_index: int = 50
        
        # Trading state
        self.active_hunts: List[OrcaOpportunity] = []
        self.completed_hunts: deque = deque(maxlen=1000)
        self.hunt_count = 0
        self.total_profit_usd = 0.0
        self.win_rate = 0.5
        
        # Symbol tracking
        self.hot_symbols: Dict[str, float] = {}  # symbol -> heat score
        self.symbol_momentum: Dict[str, float] = {}  # symbol -> momentum
        self.latest_prices: Dict[str, float] = {}
        self.price_timestamps: Dict[str, float] = {}
        
        # Risk management
        self.max_concurrent_hunts = 3
        self.daily_loss_limit_usd = -50.0
        self.daily_pnl_usd = 0.0
        self.last_hunt_time = 0.0
        self.hunt_cooldown_seconds = 5  # Minimum 5s between hunts
        
        # Persistence
        self.state_file = Path("orca_intelligence_state.json")
        self._load_state()
        
        # Counter-Intelligence wiring
        self.attribution_engine = get_attribution_engine() if COUNTER_INTEL_AVAILABLE else None
        self.counter_intel = queen_counter_intelligence if COUNTER_INTEL_AVAILABLE else None
        if COUNTER_INTEL_AVAILABLE:
            logger.info("🧠 Counter-Intelligence ENABLED for Orca")
        else:
            logger.info("🧠 Counter-Intelligence UNAVAILABLE")
        
        # 💰👁️ REAL PORTFOLIO TRACKER - NO PHANTOM NUMBERS! 👁️💰
        self.real_portfolio_tracker = None
        if REAL_PORTFOLIO_AVAILABLE and get_real_portfolio_tracker:
            try:
                self.real_portfolio_tracker = get_real_portfolio_tracker()
                logger.info("💰👁️ Real Portfolio Tracker CONNECTED - Orca sees THE TRUTH!")
            except Exception as e:
                logger.warning(f"💰⚠️ Could not connect Real Portfolio Tracker: {e}")
        
        logger.info("🦈🔪 ORCA KILLER WHALE INTELLIGENCE ACTIVATED 🔪🦈")
        logger.info(f"   Mode: {self.mode} | Max Hunts: {self.max_concurrent_hunts}")
    
    def _init_market_connections(self):
        """Initialize connections to all global market feeds."""
        market_count = 0
        
        # Kraken (crypto spot)
        if KRAKEN_AVAILABLE:
            try:
                self.kraken_client = get_kraken_client()
                market_count += 1
                logger.info("🐙 Kraken CONNECTED - Crypto spot market visibility")
            except Exception as e:
                logger.debug(f"Kraken connection failed: {e}")
        
        # Binance (REST + WebSocket)
        if BINANCE_AVAILABLE:
            try:
                self.binance_client = get_binance_client()
                market_count += 1
                logger.info("🟡 Binance REST API CONNECTED")
            except Exception as e:
                logger.debug(f"Binance connection failed: {e}")

        # Binance WebSocket (real-time crypto streaming)
        if BINANCE_WS_AVAILABLE:
            try:
                self.binance_ws = BinanceWebSocketClient()
                # Start streaming if API key available
                if os.getenv('BINANCE_API_KEY'):
                    # Orca will subscribe to top symbols later
                    market_count += 1
                    logger.info("🟡 Binance WebSocket READY - Real-time crypto streaming")
                else:
                    logger.debug("Binance API key not set - streaming unavailable")
            except Exception as e:
                logger.debug(f"Binance WS connection failed: {e}")
        
        # Alpaca (stocks + crypto)
        if ALPACA_AVAILABLE:
            try:
                self.alpaca_client = AlpacaClient()
                market_count += 1
                logger.info("🦙 Alpaca CONNECTED - Stocks + crypto market visibility")
            except Exception as e:
                logger.debug(f"Alpaca connection failed: {e}")
        
        # Capital.com (CFDs + global stocks)
        if CAPITAL_AVAILABLE:
            try:
                self.capital_client = CapitalClient()
                if self.capital_client.is_authenticated():
                    market_count += 1
                    logger.info("💼 Capital.com CONNECTED - CFD + global stock visibility")
                else:
                    self.capital_client = None
                    logger.debug("Capital.com not authenticated")
            except Exception as e:
                logger.debug(f"Capital.com connection failed: {e}")
        
        # Global Wave Scanner (market intelligence aggregator)
        if WAVE_SCANNER_AVAILABLE:
            try:
                self.wave_scanner = GlobalWaveScanner()
                market_count += 1
                logger.info("🌊 Global Wave Scanner CONNECTED - Multi-market intelligence")
            except Exception as e:
                logger.debug(f"Wave scanner init failed: {e}")
        
        # 🌊🦈🐋 Movers & Shakers Scanner (unified whale detection)
        self.movers_shakers = None
        if MOVERS_SHAKERS_AVAILABLE:
            try:
                self.movers_shakers = MoversShakersScanner(lookback_minutes=15)
                market_count += 1
                logger.info("🌊🦈🐋 Movers & Shakers Scanner CONNECTED - Unified whale detection")
            except Exception as e:
                logger.debug(f"Movers & Shakers init failed: {e}")
        
        # 🐋⚔️ Moby Dick Whale Hunter (legendary strategies)
        self.moby_dick = None
        if MOBY_DICK_AVAILABLE:
            try:
                self.moby_dick = MobyDickWhaleHunter()
                market_count += 1
                logger.info("🐋⚔️ Moby Dick Whale Hunter CONNECTED - Legendary strategies")
            except Exception as e:
                logger.debug(f"Moby Dick init failed: {e}")
        
        if market_count == 0:
            logger.warning("⚠️ NO MARKET CONNECTIONS! Orca is BLIND!")
        else:
            logger.info(f"🌐 GLOBAL MARKET VISIBILITY: {market_count} data sources connected")
    
    def scan_global_markets(self, symbols: Optional[List[str]] = None) -> List[WhaleSignal]:
        """
        Actively scan all connected markets for whale activity.
        This gives Orca proactive hunting capability across exchanges.
        
        Args:
            symbols: Optional list of symbols to scan. If None, scans all hot symbols.
        
        Returns:
            List of detected whale signals
        """
        whale_signals = []
        
        # Define symbol universe if not provided
        if symbols is None:
            symbols = self._get_hot_symbols()
        
        scan_start = time.time()
        
        # Scan Kraken
        if self.kraken_client:
            try:
                for symbol in symbols:
                    # Use get_24h_ticker for volume info
                    ticker = self.kraken_client.get_24h_ticker(symbol)
                    # {symbol, lastPrice, priceChangePercent, quoteVolume}
                    
                    if ticker and 'quoteVolume' in ticker:
                        volume_usd = float(ticker['quoteVolume'])
                        
                        # Whale threshold: $1M+ volume
                        if volume_usd >= 1_000_000:
                            signal = self._create_whale_signal(
                                symbol=symbol,
                                volume_usd=volume_usd,
                                exchange='kraken',
                                ticker_data=ticker
                            )
                            if signal:
                                whale_signals.append(signal)
            except Exception as e:
                logger.debug(f"Kraken scan error: {e}")
        
        # Scan Binance (WebSocket or REST)
        if self.binance_ws and hasattr(self.binance_ws, 'get_latest_ticker'):
            try:
                for symbol in symbols:
                    # WS usually expects clean symbols (BTCUSDT)
                    bsymbol = symbol.replace('/', '').replace('USD', 'USDT')
                    ticker = self.binance_ws.get_latest_ticker(bsymbol)
                    
                    if ticker and 'quoteVolume' in ticker:
                        volume_usd = float(ticker['quoteVolume'])
                        
                        if volume_usd >= 1_000_000:
                            signal = self._create_whale_signal(
                                symbol=symbol,
                                volume_usd=volume_usd,
                                exchange='binance',
                                ticker_data=ticker
                            )
                            if signal:
                                whale_signals.append(signal)
            except Exception as e:
                logger.debug(f"Binance WS scan error: {e}")
        elif self.binance_client:
             try:
                for symbol in symbols:
                    # REST fallback
                    bsymbol = symbol.replace('/', '').replace('USD', 'USDT')
                    ticker = self.binance_client.get_24h_ticker(bsymbol)
                    
                    if ticker and 'quoteVolume' in ticker:
                        volume_usd = float(ticker['quoteVolume'])
                        
                        if volume_usd >= 1_000_000:
                            signal = self._create_whale_signal(
                                symbol=symbol,
                                volume_usd=volume_usd,
                                exchange='binance',
                                ticker_data=ticker
                            )
                            if signal:
                                whale_signals.append(signal)
             except Exception as e:
                logger.debug(f"Binance REST scan error: {e}")
        
        # Scan Alpaca
        if self.alpaca_client:
            try:
                for symbol in symbols:
                    ticker = self.alpaca_client.get_latest_trade(symbol)
                    if ticker and 'size' in ticker:
                        # Alpaca returns trade size, need to estimate volume
                        # This is a simplified whale detection - real impl would track cumulative
                        size = float(ticker.get('size', 0))
                        price = float(ticker.get('price', 0))
                        trade_usd = size * price
                        
                        if trade_usd >= 100_000:  # $100k+ single trade = whale
                            signal = self._create_whale_signal(
                                symbol=symbol,
                                volume_usd=trade_usd,
                                exchange='alpaca',
                                ticker_data=ticker
                            )
                            if signal:
                                whale_signals.append(signal)
            except Exception as e:
                logger.debug(f"Alpaca scan error: {e}")
        
        # Use Global Wave Scanner for aggregated intelligence
        if self.wave_scanner and hasattr(self.wave_scanner, 'get_hot_opportunities'):
            try:
                opportunities = self.wave_scanner.get_hot_opportunities(min_score=0.7)
                for opp in opportunities:
                    signal = WhaleSignal(
                        timestamp=time.time(),
                        symbol=opp.get('symbol', ''),
                        side='buy' if opp.get('direction') == 'up' else 'sell',
                        volume_usd=opp.get('volume_usd', 0),
                        exchange=opp.get('exchange', 'unknown'),
                        momentum_direction=opp.get('direction', 'neutral'),
                        ride_confidence=opp.get('score', 0.5)
                    )
                    whale_signals.append(signal)
            except Exception as e:
                logger.debug(f"Wave scanner error: {e}")
        
        scan_duration = time.time() - scan_start
        
        if whale_signals:
            logger.info(f"🌊 Global scan: {len(whale_signals)} whales detected in {scan_duration:.2f}s")
        
        return whale_signals
    
    def _get_hot_symbols(self) -> List[str]:
        """Get list of hot symbols to scan across exchanges."""
        # Top crypto pairs
        hot_symbols = [
            'BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD',
            'BNB/USD', 'ADA/USD', 'DOGE/USD', 'MATIC/USD'
        ]
        
        # Add symbols with recent momentum
        for symbol, heat in list(self.symbol_heat.items())[:10]:
            if heat > 0.5 and symbol not in hot_symbols:
                hot_symbols.append(symbol)
        
        return hot_symbols
    
    def _create_whale_signal(self, symbol: str, volume_usd: float, 
                            exchange: str, ticker_data: Dict) -> Optional[WhaleSignal]:
        """Create a whale signal from ticker data."""
        try:
            # Determine direction from price movement
            side = 'buy'  # Default
            momentum_direction = 'neutral'
            
            # Try to infer from ticker data
            if 'priceChangePercent' in ticker_data:
                pct = float(ticker_data['priceChangePercent'])
                if pct > 0:
                    side = 'buy'
                    momentum_direction = 'bullish'
                elif pct < 0:
                    side = 'sell'
                    momentum_direction = 'bearish'
            
            signal = WhaleSignal(
                timestamp=time.time(),
                symbol=symbol,
                side=side,
                volume_usd=volume_usd,
                exchange=exchange,
                momentum_direction=momentum_direction,
                ride_confidence=0.6,  # Moderate confidence from scanner
                suggested_action='buy' if side == 'buy' else 'sell',
                target_pnl_pct=0.002  # 0.2% target
            )
            
            return signal
            
        except Exception as e:
            logger.debug(f"Failed to create whale signal: {e}")
            return None
    
    def _load_state(self):
        """Load persisted state."""
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text())
                self.hunt_count = data.get('hunt_count', 0)
                self.total_profit_usd = data.get('total_profit_usd', 0.0)
                self.win_rate = data.get('win_rate', 0.5)
                logger.info(f"   📊 Loaded: {self.hunt_count} hunts, ${self.total_profit_usd:.2f} profit")
        except Exception as e:
            logger.debug(f"Could not load orca state: {e}")
    
    def _save_state(self):
        """Persist state."""
        try:
            data = {
                'hunt_count': self.hunt_count,
                'total_profit_usd': self.total_profit_usd,
                'win_rate': self.win_rate,
                'queen_consultations': self.queen_consultation_count,
                'queen_approvals': self.queen_approvals,
                'queen_vetoes': self.queen_vetoes,
                'execution_orders': self.execution_orders_sent,
                'last_update': time.time()
            }
            tmp = self.state_file.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(self.state_file)
        except Exception as e:
            logger.debug(f"Could not save orca state: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 💰👁️ REAL PORTFOLIO TRACKING - NO PHANTOM NUMBERS! 👁️💰
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_real_capital(self) -> float:
        """
        Get REAL available capital for hunting.
        No phantom numbers - just the truth!
        """
        if self.real_portfolio_tracker:
            try:
                snapshot = self.real_portfolio_tracker.get_real_portfolio()
                return snapshot.total_usd
            except Exception as e:
                logger.warning(f"💰⚠️ Could not get real capital: {e}")
        return 0.0
    
    def get_real_pnl(self) -> float:
        """Get REAL realized P&L."""
        if self.real_portfolio_tracker:
            try:
                snapshot = self.real_portfolio_tracker.get_real_portfolio()
                return snapshot.realized_pnl
            except Exception as e:
                logger.warning(f"💰⚠️ Could not get real P&L: {e}")
        return 0.0
    
    def can_afford_hunt(self, min_capital: float = 5.0) -> bool:
        """
        Check if we can afford to hunt.
        Returns False if capital is too low.
        """
        real_capital = self.get_real_capital()
        if real_capital < min_capital:
            logger.warning(f"🦈💸 Cannot hunt - Only ${real_capital:.2f} available (need ${min_capital:.2f})")
            return False
        return True
    
    def log_real_status(self) -> None:
        """Log the REAL portfolio status for transparency."""
        if self.real_portfolio_tracker:
            try:
                print(self.real_portfolio_tracker.format_for_orca())
            except Exception as e:
                logger.warning(f"💰⚠️ Could not log real status: {e}")
        else:
            logger.info("💰⚠️ Real Portfolio Tracker not connected")
    
    def get_hunt_budget(self) -> float:
        """
        Calculate safe budget for next hunt based on REAL capital.
        Never risk more than 10% of actual capital.
        """
        real_capital = self.get_real_capital()
        
        # Tiered risk based on capital level
        if real_capital < 10:
            # Very low capital - be extremely conservative
            max_risk_pct = 0.02  # 2%
        elif real_capital < 50:
            max_risk_pct = 0.05  # 5%
        elif real_capital < 100:
            max_risk_pct = 0.08  # 8%
        else:
            max_risk_pct = 0.10  # 10%
        
        budget = real_capital * max_risk_pct
        
        # Minimum $1 for any trade
        if budget < 1.0 and real_capital >= 1.0:
            budget = 1.0
        
        logger.info(f"🦈💰 Hunt budget: ${budget:.2f} ({max_risk_pct:.0%} of ${real_capital:.2f})")
        return budget
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 👑 QUEEN HIERARCHY METHODS - CHAIN OF COMMAND
    # ═══════════════════════════════════════════════════════════════════════════
    
    def wire_queen(self, queen) -> bool:
        """
        Wire the Queen as supreme commander.
        Orca reports to Queen for all major decisions.
        """
        if queen is None:
            logger.warning("🦈 Cannot wire NULL Queen!")
            self.queen_connected = False
            return False
        
        self.queen = queen
        self.queen_connected = True
        logger.info(f"✅ 🦈👑 ORCA wired to QUEEN SERO - Chain of command ESTABLISHED")
        logger.info(f"   Queen object type: {type(queen)}")
        logger.info(f"   Queen has 'ask_queen_will_we_win': {hasattr(queen, 'ask_queen_will_we_win')}")
        logger.info(f"   📊 Consult threshold: ${self.QUEEN_CONSULT_THRESHOLD_USD} or <{self.QUEEN_CONSULT_CONFIDENCE:.0%} confidence")
        return True
    
    def wire_micro_profit(self, micro_profit) -> bool:
        """
        Wire the Micro Profit Engine as execution layer.
        Orca commands Micro Profit for trade execution.
        """
        if micro_profit is None:
            logger.warning("🦈 Cannot wire NULL Micro Profit!")
            return False
        
        self.micro_profit = micro_profit
        self.micro_profit_connected = True
        logger.info(f"🦈💰 ORCA wired to MICRO PROFIT - Execution channel ESTABLISHED")
        return True
    
    def wire_hft_engine(self, hft_engine) -> bool:
        """
        Wire the HFT Engine for high-frequency execution.
        Orca uses HFT for rapid whale wake riding.
        """
        if hft_engine is None:
            logger.warning("🦈 Cannot wire NULL HFT Engine!")
            return False
        
        self.hft_engine = hft_engine
        self.hft_connected = True
        logger.info(f"🦈⚡ ORCA wired to HFT ENGINE - High-frequency execution ENABLED")
        logger.info(f"   📊 Sub-10ms latency for whale wake riding")
        return True
    
    def update_market_data(self, market_data: Dict) -> None:
        """
        Update Orca's market view from Micro Profit's data.
        
        HIERARCHY: Micro Profit feeds data UP to Orca for analysis.
        
        Args:
            market_data: Dict with keys:
                - prices: {asset: price_usd}
                - ticker_cache: {symbol: {bid, ask, price, volume, ...}}
                - balances: {asset: amount}
                - momentum: {asset: momentum_pct}
                - exchange: current exchange name
        """
        prices = market_data.get('prices', {})
        ticker_cache = market_data.get('ticker_cache', {})
        momentum = market_data.get('momentum', {})
        balances = market_data.get('balances', {})
        exchange = market_data.get('exchange', 'unknown')
        
        # Update symbol momentum from Micro Profit's tracking
        for asset, mom in momentum.items():
            self.symbol_momentum[f"{asset}/USD"] = mom / 100.0  # Convert to decimal
        
        # Detect "hot" symbols based on momentum + volume
        now = time.time()
        for symbol, data in ticker_cache.items():
            if not isinstance(data, dict):
                continue
            
            base = data.get('base', '')
            price = data.get('price', 0) or data.get('last', 0)
            volume = data.get('volume', 0) or 0
            change_24h = data.get('change_24h', 0) or 0
            
            if not base or price <= 0:
                continue
            
            norm_symbol = f"{base}/USD"
            self.latest_prices[norm_symbol] = float(price)
            self.price_timestamps[norm_symbol] = now
            
            # Calculate heat score based on:
            # - Volume (whale activity)
            # - 24h change (momentum)
            # - Recent momentum
            volume_score = min(1.0, (volume * price) / 100000)  # Normalize to 100k USD
            change_score = abs(change_24h) / 5.0  # 5% = 1.0 score
            mom_score = abs(momentum.get(base, 0)) / 0.5  # 0.5%/min = 1.0 score
            
            heat = volume_score + change_score + mom_score
            
            if heat > 1.0:  # Threshold for "hot"
                self.hot_symbols[f"{base}/USD"] = heat
        
        # Look for whale-like activity (large volume spikes)
        for symbol, data in ticker_cache.items():
            if not isinstance(data, dict):
                continue
            
            base = data.get('base', '')
            volume = data.get('volume', 0) or 0
            price = data.get('price', 0) or data.get('last', 0)
            
            if not base or price <= 0:
                continue
            
            volume_usd = volume * price
            
            # Whale detection: High volume with strong momentum
            mom = momentum.get(base, 0)
            if volume_usd > 50000 and abs(mom) > 0.3:  # $50k+ volume, 0.3%+ momentum
                whale = WhaleSignal(
                    timestamp=now,
                    symbol=f"{base}/USD",
                    side='buy' if mom > 0 else 'sell',
                    volume_usd=volume_usd,
                    firm=None,
                    firm_confidence=0.0,
                    exchange=exchange,
                    momentum_direction='bullish' if mom > 0 else 'bearish',
                    ride_confidence=min(0.9, 0.5 + abs(mom)),
                    suggested_action='buy' if mom > 0 else 'sell',
                    target_pnl_pct=0.005  # 0.5% target
                )
                self.whale_signals.append(whale)
        
        logger.debug(f"🦈 Market data updated: {len(self.hot_symbols)} hot symbols, {len(self.whale_signals)} whale signals")
    
    def consult_queen(self, opportunity: OrcaOpportunity) -> Tuple[bool, str, float]:
        """
        Consult the Queen for approval on a hunting opportunity.
        
        Returns: (approved, reason, queen_confidence)
        
        The Queen evaluates:
        - Is this aligned with her wisdom?
        - Does harmonic timing favor this hunt?
        - Is the risk acceptable for her dream?
        """
        if not self.queen_connected or self.queen is None:
            logger.debug("🦈 Queen not connected - auto-approving")
            return (True, "Queen not connected - Orca autonomous", 0.5)
        
        self.queen_consultation_count += 1
        
        try:
            # Build consultation request
            request = {
                'source': 'orca_intelligence',
                'request_type': 'hunt_approval',
                'symbol': opportunity.symbol,
                'action': opportunity.action,
                'confidence': opportunity.confidence,
                'target_pnl_usd': opportunity.target_pnl_usd,
                'reasoning': opportunity.reasoning,
                'whale_signal': opportunity.whale_signal.to_dict() if hasattr(opportunity.whale_signal, 'to_dict') else None,
                'harmonic_timing': {
                    'coherence': self.harmonic_data.coherence if self.harmonic_data else 0.5,
                    'favorable': self.harmonic_data.is_favorable() if self.harmonic_data else False
                }
            }
            
            # Ask Queen using her wisdom evaluation
            queen_response = self._ask_queen_wisdom(request)
            
            approved = queen_response.get('approved', True)
            reason = queen_response.get('reason', 'Queen silent')
            queen_confidence = queen_response.get('confidence', 0.5)
            
            if approved:
                self.queen_approvals += 1
                logger.info(f"👑✅ Queen APPROVED hunt: {opportunity.symbol} ({reason})")
            else:
                self.queen_vetoes += 1
                logger.info(f"👑❌ Queen VETOED hunt: {opportunity.symbol} ({reason})")
            
            return (approved, reason, queen_confidence)
            
        except Exception as e:
            logger.warning(f"🦈 Queen consultation error: {e} - auto-approving")
            return (True, f"Consultation error: {e}", 0.5)
    
    def _ask_queen_wisdom(self, request: Dict) -> Dict:
        """
        Internal method to query Queen's wisdom.
        Uses Queen's various evaluation methods if available.
        """
        if not self.queen:
            return {'approved': True, 'reason': 'No Queen', 'confidence': 0.5}
        
        try:
            # Check if Queen has ask_queen_will_we_win method
            if hasattr(self.queen, 'ask_queen_will_we_win'):
                guidance = self.queen.ask_queen_will_we_win(
                    asset=request['symbol'],
                    exchange='orca_hunt',
                    opportunity_score=request['confidence'],
                    context={
                        'source': 'orca',
                        'action': request['action'],
                        'target_pnl': request['target_pnl_usd'],
                        'harmonic': request.get('harmonic_timing', {})
                    }
                )
                
                # Interpret guidance
                if hasattr(guidance, 'confidence'):
                    approved = guidance.confidence >= 0.5
                    return {
                        'approved': approved,
                        'reason': f"Queen confidence: {guidance.confidence:.0%}",
                        'confidence': guidance.confidence
                    }
                elif isinstance(guidance, dict):
                    approved = guidance.get('confidence', 0.5) >= 0.5
                    return {
                        'approved': approved,
                        'reason': guidance.get('reasoning', 'Queen evaluated'),
                        'confidence': guidance.get('confidence', 0.5)
                    }
            
            # Fallback: Check Queen's state
            if hasattr(self.queen, 'state'):
                from aureon.utils.aureon_queen_hive_mind import QueenState
                if self.queen.state == QueenState.HUNTING:
                    return {'approved': True, 'reason': 'Queen in HUNTING mode', 'confidence': 0.8}
                elif self.queen.state == QueenState.RESTING:
                    return {'approved': False, 'reason': 'Queen is RESTING', 'confidence': 0.2}
            
            return {'approved': True, 'reason': 'Queen permits', 'confidence': 0.6}
            
        except Exception as e:
            logger.debug(f"Queen wisdom query error: {e}")
            return {'approved': True, 'reason': f'Query error: {e}', 'confidence': 0.5}
    
    def report_hunt_outcome(self, opportunity: OrcaOpportunity, pnl_usd: float, success: bool):
        """
        Report hunt outcome back up the chain to Queen.
        Queen learns from Orca's successes and failures.
        """
        if not self.queen_connected or self.queen is None:
            return
        
        try:
            outcome_report = {
                'source': 'orca_intelligence',
                'report_type': 'hunt_outcome',
                'symbol': opportunity.symbol,
                'action': opportunity.action,
                'pnl_usd': pnl_usd,
                'success': success,
                'confidence_was': opportunity.confidence,
                'reasoning': opportunity.reasoning,
                'timestamp': time.time()
            }
            
            # Report to Queen's learning system
            if hasattr(self.queen, 'receive_child_signal'):
                self.queen.receive_child_signal(outcome_report)
            
            # Also report to loss learning if available
            if hasattr(self.queen, 'loss_learning') and self.queen.loss_learning and not success:
                self.queen.loss_learning.record_loss(
                    symbol=opportunity.symbol,
                    exchange='orca_hunt',
                    loss_amount=abs(pnl_usd),
                    reason=f"Orca hunt failed: {opportunity.reasoning[-1] if opportunity.reasoning else 'unknown'}"
                )
            
            logger.info(f"🦈👑 Reported hunt outcome to Queen: {opportunity.symbol} ${pnl_usd:+.4f} ({'WIN' if success else 'LOSS'})")
            
        except Exception as e:
            logger.debug(f"Hunt outcome report error: {e}")
    
    def request_execution(self, opportunity: OrcaOpportunity) -> Tuple[bool, str, Dict]:
        """
        Request Micro Profit Engine to execute a trade.
        
        Orca identifies opportunities, Micro Profit executes.
        
        Returns: (success, reason, execution_result)
        """
        if not self.micro_profit_connected or self.micro_profit is None:
            logger.warning("🦈 Micro Profit not connected - cannot execute")
            return (False, "Micro Profit not connected", {})
        
        self.execution_orders_sent += 1
        
        try:
            # Build execution order
            order = {
                'source': 'orca_intelligence',
                'order_type': 'orca_hunt',
                'symbol': opportunity.symbol,
                'side': opportunity.action,
                'confidence': opportunity.confidence,
                'target_pnl_usd': opportunity.target_pnl_usd,
                'position_size_pct': opportunity.position_size_pct,
                'max_hold_seconds': opportunity.max_hold_seconds,
                'stop_loss_pct': opportunity.stop_loss_pct,
                'trailing_stop_pct': opportunity.trailing_stop_pct,
                'reasoning': opportunity.reasoning,
                'orca_hunt_id': opportunity.id
            }
            
            # Send to Micro Profit for execution
            if hasattr(self.micro_profit, 'execute_orca_order'):
                result = self.micro_profit.execute_orca_order(order)
            elif hasattr(self.micro_profit, 'execute_conversion'):
                # Fallback to standard conversion
                result = {'status': 'delegated', 'method': 'standard_conversion'}
            else:
                result = {'status': 'no_method', 'error': 'Micro Profit lacks execution method'}
            
            success = self._confirm_execution(result)
            if success:
                self.execution_orders_completed += 1
            else:
                logger.warning(f"🦈💰 Execution not confirmed for {opportunity.symbol}: {result}")
            
            logger.info(f"🦈💰 Execution order {'COMPLETED' if success else 'FAILED'}: {opportunity.symbol}")
            return (success, result.get('reason', 'Executed'), result)
            
        except Exception as e:
            logger.warning(f"🦈 Execution request error: {e}")
            return (False, f"Execution error: {e}", {})

    def _is_symbol_tradeable(self, symbol: str) -> bool:
        """Block illiquid/speculative symbols and non-standard quote pairs."""
        normalized = (symbol or "").upper()
        if "/" not in normalized:
            return False
        base, quote = normalized.split("/", 1)
        if quote not in self.DEFAULT_ALLOWED_QUOTES:
            return False
        if any(token in base for token in self.BANNED_SYMBOL_TOKENS):
            return False
        if len(base) > 8:
            return False
        return True

    def _passes_profit_gate(self, opp: OrcaOpportunity) -> bool:
        """Ensure expected gross target can cover basic costs."""
        if opp.target_pnl_usd < self.MIN_TARGET_PNL_USD:
            return False
        estimated_costs = max(0.02, opp.position_size_pct * 0.5)
        return opp.target_pnl_usd > estimated_costs

    def _within_position_limits(self, opp: OrcaOpportunity) -> bool:
        """Enforce per-trade, per-symbol, and total exposure caps."""
        if opp.position_size_pct <= 0 or opp.position_size_pct > self.MAX_POSITION_SIZE_PCT:
            return False
        current_total = sum(max(0.0, h.position_size_pct) for h in self.active_hunts)
        if current_total + opp.position_size_pct > self.MAX_TOTAL_EXPOSURE_PCT:
            return False
        symbol_total = sum(
            max(0.0, h.position_size_pct) for h in self.active_hunts
            if h.symbol.upper() == opp.symbol.upper()
        )
        if symbol_total + opp.position_size_pct > self.MAX_SYMBOL_EXPOSURE_PCT:
            return False
        return True

    def _has_fresh_price(self, symbol: str) -> bool:
        ts = self.price_timestamps.get(symbol) or self.price_timestamps.get(symbol.upper())
        if not ts:
            # Fallback for environments without live feed metadata.
            return (self._get_current_price(symbol) or 0) > 0
        return (time.time() - ts) <= self.STALE_PRICE_SECONDS

    def _validate_opportunity(self, opp: OrcaOpportunity) -> bool:
        """Central validation gate before publishing or executing opportunities."""
        if opp.confidence < self.MIN_OPPORTUNITY_CONFIDENCE:
            return False
        if not self._is_symbol_tradeable(opp.symbol):
            return False
        if not self._passes_profit_gate(opp):
            return False
        if not self._within_position_limits(opp):
            return False
        if not self._has_fresh_price(opp.symbol):
            return False
        return True

    def _confirm_execution(self, result: Dict) -> bool:
        """Require explicit acknowledgement to avoid silent execution failures."""
        status = str(result.get('status', '')).lower()
        if status in {'filled', 'success'}:
            return True
        if status == 'delegated':
            return bool(result.get('order_id') or result.get('execution_id') or result.get('accepted'))
        return False
    
    def get_hierarchy_status(self) -> Dict:
        """Get the current hierarchy chain status."""
        return {
            'level': self.HIERARCHY_LEVEL,
            'name': self.HIERARCHY_NAME,
            'reports_to': self.REPORTS_TO,
            'commands': self.COMMANDS,
            'queen_connected': self.queen_connected,
            'queen_consultations': self.queen_consultation_count,
            'queen_approvals': self.queen_approvals,
            'queen_vetoes': self.queen_vetoes,
            'queen_approval_rate': self.queen_approvals / max(1, self.queen_consultation_count),
            'micro_profit_connected': self.micro_profit_connected,
            'execution_orders_sent': self.execution_orders_sent,
            'execution_orders_completed': self.execution_orders_completed,
            'execution_success_rate': self.execution_orders_completed / max(1, self.execution_orders_sent),
            'chain_integrity': self.queen_connected and self.micro_profit_connected
        }
    
    def should_consult_queen(self, opportunity: OrcaOpportunity) -> bool:
        """
        Determine if this opportunity requires Queen consultation.
        
        Consult Queen when:
        - Trade value exceeds threshold
        - Confidence is below threshold
        - High-risk hunt (whale fighting detected)
        - Queen has explicitly requested consultation
        """
        # Always consult for large trades
        estimated_value = opportunity.target_pnl_usd / 0.01  # Rough position estimate
        if estimated_value >= self.QUEEN_CONSULT_THRESHOLD_USD:
            return True
        
        # Consult for low-confidence hunts
        if opportunity.confidence < self.QUEEN_CONSULT_CONFIDENCE:
            return True
        
        # Consult if fighting whale momentum
        momentum = self.symbol_momentum.get(opportunity.symbol, 0.0)
        if opportunity.action == 'buy' and momentum < -0.3:
            return True  # Buying against bearish momentum
        if opportunity.action == 'sell' and momentum > 0.3:
            return True  # Selling against bullish momentum
        
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # INTELLIGENCE FEED INGESTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def ingest_whale_alert(self, whale_data: Dict):
        """
        Process a whale alert from the dashboard.
        This is GOLD - whales move markets!
        """
        signal = WhaleSignal(
            timestamp=time.time(),
            symbol=whale_data.get('symbol', 'BTC/USD'),
            side=whale_data.get('side', 'buy'),
            volume_usd=whale_data.get('volume_usd', whale_data.get('value_usd', 0)),
            firm=whale_data.get('firm'),
            firm_confidence=whale_data.get('firm_confidence', 0.0),
            exchange=whale_data.get('exchange', 'unknown')
        )
        
        # Calculate momentum direction
        if signal.side.lower() == 'buy':
            signal.momentum_direction = 'bullish'
            signal.suggested_action = 'buy'
        else:
            signal.momentum_direction = 'bearish'
            signal.suggested_action = 'sell'
        
        # Higher volume = higher confidence to ride
        if signal.volume_usd > 1_000_000:
            signal.ride_confidence = 0.9
            signal.target_pnl_pct = 0.003  # 0.3% for mega whales
        elif signal.volume_usd > 500_000:
            signal.ride_confidence = 0.7
            signal.target_pnl_pct = 0.002  # 0.2%
        elif signal.volume_usd > 100_000:
            signal.ride_confidence = 0.5
            signal.target_pnl_pct = 0.001  # 0.1%
        else:
            signal.ride_confidence = 0.3
            signal.target_pnl_pct = 0.0005  # 0.05%
        
        # Firm attribution boosts confidence
        if signal.firm and signal.firm_confidence > 0.7:
            signal.ride_confidence = min(1.0, signal.ride_confidence + 0.2)
            
            # Certain firms are worth following more
            smart_money_firms = ['Citadel', 'Jane Street', 'Two Sigma', 'Jump Trading']
            if any(f in signal.firm for f in smart_money_firms):
                signal.ride_confidence = min(1.0, signal.ride_confidence + 0.1)
        
        self.whale_signals.append(signal)
        self._update_symbol_heat(signal.symbol, signal.volume_usd, signal.momentum_direction)
        
        logger.info(f"🐋 Whale ingested: {signal.symbol} {signal.side.upper()} ${signal.volume_usd:,.0f} "
                   f"| Ride confidence: {signal.ride_confidence:.0%}")
        
        # 🐦 CHIRP EMISSION - kHz-Speed Whale Detection Signals
        # Emit whale detection chirps for system-wide hunting coordination
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                
                # Whale frequency mapping
                whale_freq = 880.0 if signal.side.lower() == 'buy' else 1760.0
                
                chirp_bus.emit_signal(
                    signal_type='WHALE_DETECTED',
                    symbol=signal.symbol,
                    coherence=signal.ride_confidence,
                    confidence=signal.firm_confidence if signal.firm else signal.ride_confidence,
                    frequency=whale_freq,
                    amplitude=min(1.0, signal.volume_usd / 1_000_000)  # Amplitude by volume
                )
                
            except Exception as e:
                # Chirp emission failure - non-critical, continue
                pass
        
        # Counter-Intelligence analysis: create derived signals when queen finds opportunities
        try:
            if COUNTER_INTEL_AVAILABLE and self.counter_intel:
                firm_id = None
                
                # Improved firm name → firm_id mapping
                if signal.firm:
                    # Try quick match first
                    firm_id = match_firm_name_simple(signal.firm) if match_firm_name_simple else None
                    
                    # Fall back to fuzzy match with database
                    if not firm_id and match_firm_name and self.attribution_engine:
                        match_result = match_firm_name(
                            signal.firm,
                            self.attribution_engine.firm_db,
                            threshold=0.7
                        )
                        if match_result:
                            firm_id, confidence = match_result
                            logger.info(f"🔍 Fuzzy matched '{signal.firm}' → {firm_id} (confidence: {confidence:.0%})")

                # If we found a firm id, ask queen counter-intel for a counter-signal
                if firm_id:
                    market_data = {
                        'symbol': signal.symbol,
                        'volatility': self.harmonic_data.coherence if self.harmonic_data else 0.5,
                        'volume_ratio': min(2.0, signal.volume_usd / 100000),
                        'spread_pips': 2.0,
                        'average_latency_ms': 50.0
                    }
                    bot_detection_data = {
                        'confidence': signal.ride_confidence,
                        'bot_class': None,
                        'frequency': None,
                        'layering_score': None
                    }

                    counter_signal = self.counter_intel.analyze_firm_for_counter_opportunity(
                        firm_id=firm_id,
                        market_data=market_data,
                        bot_detection_data=bot_detection_data
                    )

                    if counter_signal and counter_signal.confidence >= 0.7:
                        # Create derived whale signal to feed Orca pipeline
                        suggested_action = 'buy' if counter_signal.strategy in (
                            CounterStrategy.TIMING_ADVANTAGE,
                            CounterStrategy.PATTERN_EXPLOITATION,
                            CounterStrategy.MOMENTUM_COUNTER,
                            CounterStrategy.VOLUME_SPIKE_COUNTER
                        ) else 'sell'

                        derived_whale = WhaleSignal(
                            timestamp=time.time(),
                            symbol=signal.symbol,
                            side=signal.side,
                            volume_usd=signal.volume_usd,
                            firm=firm_id,
                            firm_confidence=counter_signal.confidence,
                            exchange=signal.exchange,
                            momentum_direction=signal.momentum_direction,
                            ride_confidence=counter_signal.confidence,
                            suggested_action=suggested_action,
                            target_pnl_pct=min(0.05, counter_signal.expected_profit_pips / 100)
                        )

                        self.whale_signals.append(derived_whale)
                        logger.info(f"🧠 Counter-intel derived whale signal appended for {signal.symbol} against {firm_id} (conf: {counter_signal.confidence:.2f})")
        except Exception as e:
            logger.debug(f"Counter-intel processing failed: {e}")

        return signal
    
    def ingest_firm_activity(self, firm_data: Dict):
        """Update firm activity tracking."""
        firm_name = firm_data.get('name', 'Unknown')
        self.firm_activity[firm_name] = {
            'count': firm_data.get('count', 0),
            'hq': firm_data.get('hq', 'Unknown'),
            'capital': firm_data.get('capital', 0),
            'animal': firm_data.get('animal', '🤖'),
            'last_seen': time.time()
        }
    
    def ingest_market_thesis(self, thesis: Dict):
        """Update market thesis from Deep Intelligence."""
        self.market_thesis = thesis
        logger.debug(f"📊 Thesis updated: {thesis.get('regime', 'neutral')}")
    
    def ingest_harmonic_data(self, harmonic: Dict):
        """Update harmonic resonance data."""
        self.harmonic_data = HarmonicTiming(
            schumann_alignment=harmonic.get('schumann', 0.5),
            phi_alignment=harmonic.get('phi', 0.5),
            love_alignment=harmonic.get('love', 0.5),
            coherence=harmonic.get('coherence', 0.5)
        )
    
    def ingest_fear_greed(self, index: int):
        """Update Fear & Greed index."""
        self.fear_greed_index = index
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🌊🦈🐋 MOVERS & SHAKERS INTEGRATION - WHO'S MAKING THE WAVES?
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def scan_movers_shakers(self) -> List[WhaleSignal]:
        """
        🌊 SCAN FOR MOVERS & SHAKERS 🌊
        
        Uses the unified Movers & Shakers Scanner to identify:
        - 🐋 WHALES - Large institutional players
        - 🦈 SHARKS - HFT algorithms
        - 🐙 OCTOPI - Market manipulators (AVOID)
        - 🐬 DOLPHINS - Smart money
        - 🦑 SQUIDS - Dark pool operators
        
        Returns: List of whale signals derived from detected movers
        """
        if not self.movers_shakers:
            logger.debug("🌊 Movers & Shakers scanner not available")
            return []
        
        try:
            # Run the unified scan
            report = await self.movers_shakers.run_scan()
            
            whale_signals = []
            
            # Process each category of movers
            for mover in report.all_movers:
                # Skip manipulators - don't trade against them
                if MOVERS_SHAKERS_AVAILABLE and mover.wave_type == WaveType.OCTOPUS:
                    logger.warning(f"🐙 OCTOPUS DETECTED on {mover.symbol} - AVOIDING")
                    continue
                
                # Convert mover to whale signal
                signal = self._mover_to_whale_signal(mover)
                if signal:
                    whale_signals.append(signal)
                    self.whale_signals.append(signal)
            
            # Log summary
            if whale_signals:
                logger.info(f"🌊 Movers & Shakers scan: {len(whale_signals)} actionable signals")
                logger.info(f"   Net Flow: {report.net_flow_direction}")
                logger.info(f"   Whale Consensus: {report.whale_consensus}")
                if report.manipulation_alert:
                    logger.warning(f"   ⚠️ MANIPULATION ALERT - Trade carefully!")
            
            return whale_signals
            
        except Exception as e:
            logger.error(f"🌊 Movers & Shakers scan error: {e}")
            return []
    
    def _mover_to_whale_signal(self, mover) -> Optional[WhaleSignal]:
        """
        Convert a MoverShaker detection to a WhaleSignal for Orca processing.
        """
        try:
            # Map wave type to momentum direction
            if mover.side == 'buy':
                momentum_direction = 'bullish'
                suggested_action = 'buy'
            elif mover.side == 'sell':
                momentum_direction = 'bearish'
                suggested_action = 'sell'
            else:
                momentum_direction = 'neutral'
                suggested_action = 'hold'
            
            # Map wave type to ride confidence
            ride_confidence = 0.5  # Base
            if MOVERS_SHAKERS_AVAILABLE:
                if mover.wave_type == WaveType.WHALE:
                    ride_confidence = 0.85  # High confidence for whales
                elif mover.wave_type == WaveType.SHARK:
                    ride_confidence = 0.7   # Good for HFT
                elif mover.wave_type == WaveType.DOLPHIN:
                    ride_confidence = 0.6   # Smart money
                elif mover.wave_type == WaveType.SQUID:
                    ride_confidence = 0.5   # Hidden liquidity
            
            # Boost confidence if firm attributed
            if mover.attributed_firm and mover.firm_confidence > 0.5:
                ride_confidence = min(1.0, ride_confidence + 0.1)
            
            # Target PnL based on volume
            if mover.volume_usd > 100_000:
                target_pnl_pct = 0.003  # 0.3% for mega movers
            elif mover.volume_usd > 25_000:
                target_pnl_pct = 0.002  # 0.2% for sharks
            else:
                target_pnl_pct = 0.001  # 0.1% for dolphins
            
            signal = WhaleSignal(
                timestamp=mover.timestamp,
                symbol=mover.symbol,
                side=mover.side,
                volume_usd=mover.volume_usd,
                firm=mover.attributed_firm,
                firm_confidence=mover.firm_confidence,
                exchange=mover.exchange,
                momentum_direction=momentum_direction,
                ride_confidence=ride_confidence,
                suggested_action=suggested_action,
                target_pnl_pct=target_pnl_pct
            )
            
            return signal
            
        except Exception as e:
            logger.debug(f"Failed to convert mover to signal: {e}")
            return None
    
    def scan_moby_dick_predictions(self) -> List[WhaleSignal]:
        """
        🐋⚔️ MOBY DICK WHALE PREDICTIONS ⚔️🐋
        
        Uses Captain Ahab's legendary strategies to predict whale movements:
        - GAM System: Information from other exchanges
        - Fedallah's Prophecies: Pattern-based predictions
        - The Three Harpoons: Triple validation before execution
        
        Returns: List of predicted whale signals
        """
        if not self.moby_dick:
            return []
        
        try:
            predictions = []
            
            # Get whale predictions if available
            if hasattr(self.moby_dick, 'predict_whale_surfacing'):
                symbols = self._get_hot_symbols()
                for symbol in symbols[:5]:  # Top 5 hot symbols
                    prediction = self.moby_dick.predict_whale_surfacing(symbol)
                    if prediction and prediction.confidence >= 0.6:
                        signal = WhaleSignal(
                            timestamp=time.time(),
                            symbol=prediction.symbol,
                            side=prediction.predicted_side,
                            volume_usd=prediction.estimated_volume_usd if hasattr(prediction, 'estimated_volume_usd') else 50000,
                            momentum_direction='bullish' if prediction.predicted_side == 'buy' else 'bearish',
                            ride_confidence=prediction.confidence,
                            suggested_action=prediction.predicted_side,
                            target_pnl_pct=0.002
                        )
                        predictions.append(signal)
                        logger.info(f"🐋⚔️ Moby Dick predicts: {symbol} {prediction.predicted_side.upper()} (conf: {prediction.confidence:.0%})")
            
            # Get GAM encounters (cross-exchange intelligence)
            if hasattr(self.moby_dick, 'get_gam_encounters'):
                encounters = self.moby_dick.get_gam_encounters()
                for enc in encounters[-5:]:  # Last 5 encounters
                    if enc.confidence >= 0.6:
                        signal = WhaleSignal(
                            timestamp=enc.timestamp,
                            symbol=enc.symbol,
                            side='buy' if enc.whale_class == 'ACCUMULATION_BOT' else 'sell',
                            volume_usd=enc.activities * 10000,  # Estimate
                            firm=None,
                            exchange=enc.exchange,
                            momentum_direction='bullish' if enc.whale_class == 'ACCUMULATION_BOT' else 'bearish',
                            ride_confidence=enc.confidence,
                            suggested_action='buy' if enc.whale_class == 'ACCUMULATION_BOT' else 'sell',
                            target_pnl_pct=0.002
                        )
                        predictions.append(signal)
            
            return predictions
            
        except Exception as e:
            logger.debug(f"Moby Dick prediction error: {e}")
            return []
    
    def get_wave_consensus(self) -> Dict[str, Any]:
        """
        🌊 GET OVERALL WAVE CONSENSUS 🌊
        
        Aggregates all wave detection systems to determine market direction.
        
        Returns: Dict with consensus information
        """
        consensus = {
            'timestamp': time.time(),
            'net_direction': 'neutral',
            'confidence': 0.5,
            'whale_count': 0,
            'shark_count': 0,
            'manipulation_detected': False,
            'recommended_action': 'hold',
            'sources': []
        }
        
        # Count recent signals by direction
        now = time.time()
        recent_signals = [s for s in self.whale_signals if now - s.timestamp < 300]  # 5 min
        
        buy_signals = [s for s in recent_signals if s.side == 'buy']
        sell_signals = [s for s in recent_signals if s.side == 'sell']
        
        buy_volume = sum(s.volume_usd for s in buy_signals)
        sell_volume = sum(s.volume_usd for s in sell_signals)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            buy_ratio = buy_volume / total_volume
            
            if buy_ratio > 0.65:
                consensus['net_direction'] = 'bullish'
                consensus['recommended_action'] = 'buy'
                consensus['confidence'] = buy_ratio
            elif buy_ratio < 0.35:
                consensus['net_direction'] = 'bearish'
                consensus['recommended_action'] = 'sell'
                consensus['confidence'] = 1 - buy_ratio
            else:
                consensus['net_direction'] = 'neutral'
                consensus['recommended_action'] = 'hold'
                consensus['confidence'] = 0.5
        
        consensus['whale_count'] = len([s for s in recent_signals if s.volume_usd > 100000])
        consensus['shark_count'] = len([s for s in recent_signals if 25000 <= s.volume_usd < 100000])
        
        # Check for manipulation (lots of signals but no clear direction)
        if len(recent_signals) > 10 and consensus['confidence'] < 0.55:
            consensus['manipulation_detected'] = True
        
        return consensus
    
    def _update_symbol_heat(self, symbol: str, volume: float, direction: str):
        """Track symbol 'heat' - how active/attractive it is."""
        current_heat = self.hot_symbols.get(symbol, 0.0)
        heat_delta = volume / 1_000_000  # Normalize by $1M
        
        # Decay existing heat
        current_heat *= 0.95
        
        # Add new heat
        current_heat += heat_delta
        
        self.hot_symbols[symbol] = min(10.0, current_heat)  # Cap at 10
        
        # Update momentum
        current_momentum = self.symbol_momentum.get(symbol, 0.0)
        if direction == 'bullish':
            current_momentum = current_momentum * 0.8 + 0.2
        elif direction == 'bearish':
            current_momentum = current_momentum * 0.8 - 0.2
        else:
            current_momentum *= 0.9
        
        self.symbol_momentum[symbol] = max(-1.0, min(1.0, current_momentum))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HUNTING LOGIC - WHERE THE MAGIC HAPPENS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def scan_for_opportunities(self) -> List[OrcaOpportunity]:
        """
        🦈🔪 THE HUNT BEGINS 🔪🦈
        
        Analyze all intelligence to find the best whale wakes to ride.
        Now includes:
        - 🐋 Recent Whale Activity (direct detections)
        - 🐋⚔️ Moby Dick Predictions (legendary strategies)
        - 🔥 Hot Symbol Momentum
        - 📊 Market Thesis Alignment
        - 😱 Fear & Greed Contrarian
        - 🌊 Wave Consensus Filtering
        """
        print("DEBUG: Inside Orca scan_for_opportunities method!")
        logger.info("DEBUG: Entering scan_for_opportunities")
        opportunities = []
        now = time.time()
        
        # Check cooldown
        if now - self.last_hunt_time < self.hunt_cooldown_seconds:
            logger.info(f"DEBUG: Cooldown active ({now - self.last_hunt_time:.1f}s < {self.hunt_cooldown_seconds}s)")
            return []
        
        # Check risk limits
        if self.daily_pnl_usd <= self.daily_loss_limit_usd:
            logger.warning(f"🛑 Daily loss limit reached: ${self.daily_pnl_usd:.2f}")
            self.mode = "RESTING"
            return []
        
        # Check concurrent hunt limit
        if len(self.active_hunts) >= self.max_concurrent_hunts:
            logger.info(f"DEBUG: Max concurrent hunts reached ({len(self.active_hunts)})")
            return []
        
        # === SIGNAL 0: Moby Dick Whale Predictions ===
        moby_predictions = self.scan_moby_dick_predictions()
        for prediction in moby_predictions:
            self.whale_signals.append(prediction)
            logger.info(f"🐋⚔️ Moby Dick prediction added: {prediction.symbol} {prediction.side}")
        
        # === SIGNAL 1: Recent Whale Activity ===
        recent_whales = [w for w in self.whale_signals if now - w.timestamp < 60]  # Last 60s
        logger.info(f"DEBUG: Found {len(recent_whales)} recent whales. Total signals: {len(self.whale_signals)}")

        for whale in recent_whales:
            # Skip if already hunting this symbol
            if any(h.symbol == whale.symbol for h in self.active_hunts):
                logger.info(f"DEBUG: Skipping {whale.symbol} - Already hunting")
                continue
            
            # Check harmonic timing
            timing_ok = True
            timing_mult = 1.0
            if self.harmonic_data:
                timing_ok = self.harmonic_data.is_favorable()
                timing_mult = self.harmonic_data.timing_multiplier()
            
            logger.info(f"DEBUG: Evaluating {whale.symbol}: Conf={whale.ride_confidence}, Timing={timing_ok}")

            # Build opportunity if whale confidence is high enough
            if whale.ride_confidence >= 0.1 and timing_ok:
                opp = self._build_opportunity_from_whale(whale, timing_mult)
                if opp and self._validate_opportunity(opp):
                    opportunities.append(opp)
                    logger.info(f"DEBUG: Added opp for {whale.symbol}")
                else:
                    logger.info(f"DEBUG: _build_opportunity_from_whale returned None")
            else:
                 logger.info(f"DEBUG: Rejected {whale.symbol} - Threshold/Timing failed")
        
        # === SIGNAL 2: Hot Symbol Momentum ===
        for symbol, heat in self.hot_symbols.items():
            if heat < 2.0:  # Need at least 2.0 heat score
                continue
            
            # Skip if already hunting
            if any(h.symbol == symbol for h in self.active_hunts):
                continue
            
            momentum = self.symbol_momentum.get(symbol, 0.0)
            if abs(momentum) > 0.3:  # Strong momentum either way
                opp = self._build_opportunity_from_momentum(symbol, heat, momentum)
                if opp and self._validate_opportunity(opp):
                    opportunities.append(opp)
        
        # === SIGNAL 3: Market Thesis Alignment ===
        if self.market_thesis:
            regime = self.market_thesis.get('regime', 'neutral')
            if regime in ['bull', 'bullish', 'accumulation']:
                # Favor long positions
                for opp in opportunities:
                    if opp.action == 'buy':
                        opp.confidence = min(1.0, opp.confidence + 0.1)
                        opp.reasoning.append(f"Thesis alignment: {regime} regime")
            elif regime in ['bear', 'bearish', 'distribution']:
                # Favor short positions
                for opp in opportunities:
                    if opp.action == 'sell':
                        opp.confidence = min(1.0, opp.confidence + 0.1)
                        opp.reasoning.append(f"Thesis alignment: {regime} regime")
        
        # === SIGNAL 4: Fear & Greed Contrarian ===
        if self.fear_greed_index < 25:  # Extreme fear
            for opp in opportunities:
                if opp.action == 'buy':
                    opp.confidence = min(1.0, opp.confidence + 0.15)
                    opp.reasoning.append(f"Contrarian: Extreme Fear ({self.fear_greed_index})")
        elif self.fear_greed_index > 75:  # Extreme greed
            for opp in opportunities:
                if opp.action == 'sell':
                    opp.confidence = min(1.0, opp.confidence + 0.15)
                    opp.reasoning.append(f"Contrarian: Extreme Greed ({self.fear_greed_index})")
        
        # === SIGNAL 5: Wave Consensus Filtering ===
        wave_consensus = self.get_wave_consensus()
        if wave_consensus['manipulation_detected']:
            # Reduce all confidence when manipulation detected
            logger.warning("🐙 MANIPULATION DETECTED - Reducing confidence on all opportunities")
            for opp in opportunities:
                opp.confidence *= 0.7
                opp.reasoning.append("⚠️ Manipulation detected - confidence reduced")
        elif wave_consensus['confidence'] > 0.7:
            # Boost opportunities aligned with wave consensus
            for opp in opportunities:
                if opp.action == wave_consensus['recommended_action']:
                    opp.confidence = min(1.0, opp.confidence + 0.1)
                    opp.reasoning.append(f"🌊 Wave consensus: {wave_consensus['net_direction']} ({wave_consensus['confidence']:.0%})")
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x.confidence, reverse=True)
        
        # 👑 QUEEN CONSULTATION - Filter through chain of command
        approved_opportunities = []
        for opp in opportunities[:5]:  # Consider top 5 candidates
            if not self._validate_opportunity(opp):
                continue
            if self.should_consult_queen(opp):
                approved, reason, queen_conf = self.consult_queen(opp)
                if approved:
                    opp.reasoning.append(f"👑 Queen approved: {reason}")
                    opp.confidence = (opp.confidence + queen_conf) / 2  # Blend confidence
                    approved_opportunities.append(opp)
                else:
                    opp.reasoning.append(f"👑 Queen VETOED: {reason}")
                    logger.info(f"🦈👑 Hunt VETOED by Queen: {opp.symbol} - {reason}")
            else:
                # Low-risk hunt - proceed without consultation
                opp.reasoning.append("🦈 Autonomous hunt (below consultation threshold)")
                approved_opportunities.append(opp)
        
        # Publish and return top 3 approved opportunities
        final_opportunities = approved_opportunities[:3]
        for opp in final_opportunities:
            self._publish_opportunity(opp)
            
        return final_opportunities
    
    def _build_opportunity_from_whale(self, whale: WhaleSignal, timing_mult: float) -> Optional[OrcaOpportunity]:
        """Build a trading opportunity from a whale signal."""
        self.hunt_count += 1
        
        # Calculate position size
        base_size_pct = 0.02  # 2% base
        confidence_adjusted = base_size_pct * whale.ride_confidence * timing_mult
        
        # Calculate target PnL
        target_pnl_pct = whale.target_pnl_pct
        target_pnl_usd = max(0.10, target_pnl_pct * 1000)  # Assume $1000 base
        
        reasoning = [
            f"Whale detected: ${whale.volume_usd:,.0f} {whale.side}",
            f"Ride confidence: {whale.ride_confidence:.0%}",
        ]
        
        if whale.firm:
            reasoning.append(f"Firm: {whale.firm} ({whale.firm_confidence:.0%})")
        
        if self.harmonic_data:
            reasoning.append(f"Harmonic coherence: {self.harmonic_data.coherence:.0%}")
        
        return OrcaOpportunity(
            id=f"ORCA-{self.hunt_count:06d}",
            timestamp=time.time(),
            symbol=whale.symbol,
            action=whale.suggested_action,
            whale_signal=whale,
            firm_attribution=whale.firm,
            confidence=whale.ride_confidence,
            harmonic_timing=self.harmonic_data,
            position_size_pct=min(self.MAX_POSITION_SIZE_PCT, confidence_adjusted),
            target_pnl_usd=target_pnl_usd,
            max_hold_seconds=300 if whale.volume_usd < 500_000 else 600,
            reasoning=reasoning
        )
    
    def _build_opportunity_from_momentum(self, symbol: str, heat: float, momentum: float) -> Optional[OrcaOpportunity]:
        """Build opportunity from symbol momentum."""
        self.hunt_count += 1
        
        action = 'buy' if momentum > 0 else 'sell'
        confidence = min(1.0, abs(momentum) + heat / 10)
        
        reasoning = [
            f"Hot symbol: heat={heat:.1f}",
            f"Momentum: {momentum:+.2f} ({'bullish' if momentum > 0 else 'bearish'})",
        ]
        
        return OrcaOpportunity(
            id=f"ORCA-M-{self.hunt_count:06d}",
            timestamp=time.time(),
            symbol=symbol,
            action=action,
            confidence=confidence,
            position_size_pct=min(self.MAX_POSITION_SIZE_PCT, 0.01 * (heat / 2)),
            target_pnl_usd=0.15,  # $0.15 target
            max_hold_seconds=180,  # 3 minutes
            reasoning=reasoning
        )
    
    def _publish_opportunity(self, opp: OrcaOpportunity) -> None:
        """Publish an approved opportunity to the ThoughtBus and ChirpBus."""
        try:
            # 1. ThoughtBus (Neural Log)
            if self.thought_bus:
                thought = Thought(
                    source="ORCA_INTELLIGENCE",
                    thought_type="HUNT_OPPORTUNITY",
                    priority=1,  # High priority
                    content={
                        "symbol": opp.symbol,
                        "action": opp.action,
                        "confidence": opp.confidence,
                        "reasoning": opp.reasoning,
                        "target_pnl": opp.target_pnl_usd,
                        "id": opp.id
                    }
                )
                self.thought_bus.publish(thought)

            # 2. ChirpBus (High Speed)
            if self.chirp_bus:
                payload = {
                    "symbol": opp.symbol,
                    "action": opp.action,
                    "conf": opp.confidence,
                    "src": "ORCA"
                }
                self.chirp_bus.publish("orca.hunt.opportunity", payload)
                
            logger.info(f"Published ORCA opportunity: {opp.symbol} {opp.action} (Conf: {opp.confidence:.2f})")

        except Exception as e:
            logger.error(f"Failed to publish ORCA opportunity: {e}")

    def start_hunt(self, opportunity: OrcaOpportunity) -> bool:
        """
        Begin tracking an active hunt.
        
        HIERARCHY: Orca commands Micro Profit for execution.
        
        Returns: True if hunt started successfully, False if blocked.
        """
        if not self._validate_opportunity(opportunity):
            logger.info(f"🦈🛑 Hunt blocked by risk/quality gates: {opportunity.symbol}")
            return False
        
        # 👑 Final Queen check (emergency veto)
        if self.queen_connected and self.queen:
            try:
                if hasattr(self.queen, 'state'):
                    from aureon.utils.aureon_queen_hive_mind import QueenState
                    if self.queen.state == QueenState.RESTING:
                        logger.info(f"🦈👑 Hunt BLOCKED - Queen is RESTING")
                        return False
            except Exception:
                pass
        
        logger.info(f"🦈🔪 HUNT STARTED: {opportunity.id}")
        logger.info(f"   Symbol: {opportunity.symbol} | Action: {opportunity.action.upper()}")
        logger.info(f"   Confidence: {opportunity.confidence:.0%} | Target: ${opportunity.target_pnl_usd:.2f}")
        for r in opportunity.reasoning:
            logger.info(f"   • {r}")
        
        # � CHIRP EMISSION - kHz-Speed Hunt Start Signals
        # Emit hunt start chirps for coordinated multi-system hunting
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                
                # Hunt direction frequency
                hunt_freq = 880.0 if opportunity.action.lower() == 'buy' else 1760.0
                
                chirp_bus.emit_signal(
                    signal_type='ORCA_HUNT_START',
                    symbol=opportunity.symbol,
                    coherence=opportunity.confidence,
                    confidence=opportunity.confidence,
                    frequency=hunt_freq,
                    amplitude=opportunity.position_size_pct
                )
                
            except Exception as e:
                # Chirp emission failure - non-critical, continue
                pass
        
        # �💰 COMMAND MICRO PROFIT - Request execution
        if self.micro_profit_connected:
            success, reason, result = self.request_execution(opportunity)
            if success:
                self.active_hunts.append(opportunity)
                opportunity.entry_timestamp = time.time()
                opportunity.entry_price = opportunity.entry_price or self._get_current_price(opportunity.symbol) or 0.0
                self.last_hunt_time = time.time()
                self.mode = "HUNTING"
                logger.info(f"🦈💰 Execution delegated to Micro Profit: {reason}")
            else:
                logger.warning(f"🦈💰 Execution request failed: {reason}")
                return False
        else:
            logger.warning("🦈💰 Micro Profit not connected - hunt not started")
            return False
        
        # Save state
        self._save_state()
        
        return True
    
    def manage_active_hunts(self) -> List[Tuple[OrcaOpportunity, str, float]]:
        """
        🦈🔪 CLEAN KILL MANAGEMENT 🔪🦈
        
        Check all active hunts for exit conditions.
        Returns list of (opportunity, exit_reason, exit_size) tuples.
        """
        exits = []
        
        for hunt in self.active_hunts[:]:  # Copy to avoid modification during iteration
            # Get current price (would come from price feed)
            current_price = self._get_current_price(hunt.symbol)
            if not current_price:
                continue
            
            # Update price tracking for dynamic exits
            hunt.update_price(current_price)
            
            # Check exit conditions
            should_exit, exit_reason = hunt.should_exit(current_price, self)
            
            if should_exit:
                # Calculate exit size (partial or full)
                exit_size = hunt.calculate_exit_size(current_price)
                
                exits.append((hunt, exit_reason, exit_size))
                
                # Remove from active hunts if full exit
                if exit_size >= 1.0 or hunt.partial_exited:
                    self.active_hunts.remove(hunt)
                    self.completed_hunts.append(hunt)
                    
                    logger.info(f"🦈🔪 HUNT COMPLETED: {hunt.id}")
                    logger.info(f"   Exit: {exit_reason}")
                    logger.info(f"   Held: {time.time() - hunt.entry_timestamp:.0f}s")
                    
                    # Update mode
                    if not self.active_hunts:
                        self.mode = "STALKING"
        
        return exits
    
    def execute_clean_exit(self, hunt: OrcaOpportunity, exit_reason: str, exit_size: float, 
                          actual_pnl_usd: float) -> None:
        """
        Execute a clean exit and update tracking.
        
        HIERARCHY: Report outcome back to Queen for learning.
        """
        # Update win/loss tracking
        is_win = actual_pnl_usd > 0
        self.completed_hunts.append(hunt)
        
        # Store actual PnL on hunt for reference
        hunt.actual_pnl_usd = actual_pnl_usd
        
        # Update statistics
        self.total_profit_usd += actual_pnl_usd
        self.daily_pnl_usd += actual_pnl_usd
        
        # Update win rate (rolling average)
        if len(self.completed_hunts) > 10:
            recent_hunts = list(self.completed_hunts)[-10:]
            wins = sum(1 for h in recent_hunts if getattr(h, 'actual_pnl_usd', 0) > 0)
            self.win_rate = wins / len(recent_hunts)
        
        logger.info(f"🦈🔪 CLEAN EXIT EXECUTED: {hunt.id}")
        logger.info(f"   Reason: {exit_reason}")
        logger.info(f"   PnL: ${actual_pnl_usd:+.4f}")
        logger.info(f"   Win Rate: {self.win_rate:.0%}")
        
        # 👑 REPORT TO QUEEN - Chain of command feedback
        self.report_hunt_outcome(hunt, actual_pnl_usd, is_win)
        
        # Update mode based on performance
        if self.daily_pnl_usd <= self.daily_loss_limit_usd:
            self.mode = "RESTING"
            logger.warning(f"🦈😴 Daily loss limit reached - RESTING")
        elif is_win:
            self.mode = "FEEDING"  # Successful kill - in feeding mode
        else:
            self.mode = "STALKING"  # Failed hunt - back to stalking
        
        # Save state
        self._save_state()
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        This would integrate with the price feed system.
        """
        # For now, return a mock price - in real implementation this would
        # query the actual price feed (Kraken, Binance, etc.)
        # Stage AN: was hardcoded {'BTC/USD': 95000, 'ETH/USD': 3200, ...}
        # with $100 default for unknown symbols. Replaced with real-data
        # fallback chain — exit signals broadcast to the dashboard now reflect
        # real prices, not stale references that distorted exit recommendations.

        if symbol in self.latest_prices:
            return self.latest_prices[symbol]
        if symbol.upper() in self.latest_prices:
            return self.latest_prices[symbol.upper()]
        try:
            from aureon.observer.real_price_fallback import get_real_price
            price = get_real_price(symbol, max_cache_age_sec=60.0, timeout_sec=3.0)
            if price and price > 0:
                # Cache so subsequent calls are free
                self.latest_prices[symbol] = float(price)
                return float(price)
        except Exception:
            pass
        # Real chain failed and we have no cache — return 0.0 sentinel
        # (exit-signal logic will see "no real price" and skip).
        return 0.0
    
    def get_exit_signals(self) -> List[Dict]:
        """
        Get all current exit signals for active hunts.
        Used by dashboard to show exit recommendations.
        """
        signals = []
        
        for hunt in self.active_hunts:
            current_price = self._get_current_price(hunt.symbol)
            if not current_price:
                continue
            
            should_exit, exit_reason = hunt.should_exit(current_price, self)
            
            if should_exit:
                signals.append({
                    'hunt_id': hunt.id,
                    'symbol': hunt.symbol,
                    'action': hunt.action,
                    'entry_price': hunt.entry_price,
                    'current_price': current_price,
                    'exit_reason': exit_reason,
                    'exit_size': hunt.calculate_exit_size(current_price),
                    'potential_pnl': (current_price - hunt.entry_price) * (1 if hunt.action == 'buy' else -1),
                    'time_held': time.time() - hunt.entry_timestamp
                })
        
        return signals
        
        self._save_state()
    
    def complete_hunt(self, opportunity_id: str, pnl_usd: float, exit_reason: str = "target_hit"):
        """Complete a hunt and record results."""
        hunt = None
        for h in self.active_hunts:
            if h.id == opportunity_id:
                hunt = h
                break
        
        if not hunt:
            return
        
        self.active_hunts.remove(hunt)
        self.completed_hunts.append({
            'id': hunt.id,
            'symbol': hunt.symbol,
            'action': hunt.action,
            'pnl_usd': pnl_usd,
            'exit_reason': exit_reason,
            'timestamp': time.time()
        })
        
        # Update stats
        self.total_profit_usd += pnl_usd
        self.daily_pnl_usd += pnl_usd
        
        # Update win rate
        recent = list(self.completed_hunts)[-100:]
        wins = sum(1 for h in recent if h['pnl_usd'] > 0)
        self.win_rate = wins / len(recent) if recent else 0.5
        
        if len(self.active_hunts) == 0:
            self.mode = "STALKING"
        
        emoji = "🎯" if pnl_usd > 0 else "❌"
        logger.info(f"{emoji} HUNT COMPLETE: {hunt.id} | PnL: ${pnl_usd:+.2f} | {exit_reason}")
        logger.info(f"   📊 Total: ${self.total_profit_usd:.2f} | Win Rate: {self.win_rate:.0%}")
        
        # 🐦 CHIRP EMISSION - kHz-Speed Hunt Complete Signals
        # Emit hunt completion chirps for system-wide profit tracking
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                
                # Win/loss frequency
                result_freq = 528.0 if pnl_usd > 0 else 220.0  # Love freq for wins, trough for losses
                
                chirp_bus.emit_signal(
                    signal_type='ORCA_HUNT_COMPLETE',
                    symbol=hunt.symbol,
                    coherence=self.win_rate,
                    confidence=abs(pnl_usd) / 10.0 if pnl_usd != 0 else 0.1,  # Confidence based on PnL size
                    frequency=result_freq,
                    amplitude=min(1.0, abs(pnl_usd) / 50.0)  # Amplitude by PnL magnitude
                )
                
            except Exception as e:
                # Chirp emission failure - non-critical, continue
                pass
        
        self._save_state()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRATION WITH MICRO PROFIT LABYRINTH
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_orca_boost(self, symbol: str, base_score: float) -> Tuple[float, List[str]]:
        """
        Get a score boost for a symbol based on Orca intelligence.
        This integrates with micro_profit_labyrinth's scoring.
        
        Returns: (boost_multiplier, reasoning_list)
        """
        boost = 1.0
        reasons = []
        
        # Check recent whale activity on this symbol
        now = time.time()
        recent_whales = [w for w in self.whale_signals 
                        if symbol in w.symbol and now - w.timestamp < 120]
        
        if recent_whales:
            best_whale = max(recent_whales, key=lambda w: w.volume_usd)
            boost += 0.3 * best_whale.ride_confidence
            reasons.append(f"🐋 Whale wake: ${best_whale.volume_usd:,.0f}")
        
        # Check symbol heat
        heat = self.hot_symbols.get(symbol, 0.0)
        if heat > 1.0:
            boost += 0.1 * min(heat, 5.0)
            reasons.append(f"🔥 Hot symbol: {heat:.1f}")
        
        # Check harmonic timing
        if self.harmonic_data and self.harmonic_data.is_favorable():
            boost += 0.15
            reasons.append(f"🔮 Harmonic coherence: {self.harmonic_data.coherence:.0%}")
        
        # Check thesis alignment
        if self.market_thesis:
            regime = self.market_thesis.get('regime', 'neutral')
            if regime in ['bull', 'bullish']:
                boost += 0.1
                reasons.append(f"📈 Bull thesis")
        
        return (boost, reasons)
    
    def should_execute_trade(self, symbol: str, side: str, amount_usd: float) -> Tuple[bool, str]:
        """
        Final gate check before executing a trade.
        Returns: (should_execute, reason)
        """
        # Check daily limits
        if self.daily_pnl_usd <= self.daily_loss_limit_usd:
            return (False, "Daily loss limit reached")
        
        # Check harmonic timing for larger trades
        if amount_usd > 100 and self.harmonic_data:
            if self.harmonic_data.coherence < 0.4:
                return (False, f"Low harmonic coherence: {self.harmonic_data.coherence:.0%}")
        
        # Check if we're fighting whale momentum
        momentum = self.symbol_momentum.get(symbol, 0.0)
        if side == 'buy' and momentum < -0.5:
            return (False, "Fighting bearish whale momentum")
        if side == 'sell' and momentum > 0.5:
            return (False, "Fighting bullish whale momentum")
        
        return (True, "Orca approved")
    
    def get_status(self) -> Dict:
        """Get current Orca status for dashboard including hierarchy info."""
        hierarchy = self.get_hierarchy_status()
        return {
            'enabled': self.enabled,
            'mode': self.mode,
            'hunt_count': self.hunt_count,
            'active_hunts': len(self.active_hunts),
            'total_profit_usd': self.total_profit_usd,
            'daily_pnl_usd': self.daily_pnl_usd,
            'win_rate': self.win_rate,
            'hot_symbols': dict(sorted(self.hot_symbols.items(), key=lambda x: x[1], reverse=True)[:5]),
            'recent_whales': len([w for w in self.whale_signals if time.time() - w.timestamp < 300]),
            'harmonic_favorable': self.harmonic_data.is_favorable() if self.harmonic_data else False,
            'coherence': self.harmonic_data.coherence if self.harmonic_data else 0.5,
            # 👑 HIERARCHY STATUS
            'hierarchy': {
                'level': hierarchy['level'],
                'name': hierarchy['name'],
                'queen_connected': hierarchy['queen_connected'],
                'queen_approval_rate': hierarchy['queen_approval_rate'],
                'micro_profit_connected': hierarchy['micro_profit_connected'],
                'execution_success_rate': hierarchy['execution_success_rate'],
                'chain_integrity': hierarchy['chain_integrity']
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_orca_instance: Optional[OrcaKillerWhaleIntelligence] = None

def get_orca() -> OrcaKillerWhaleIntelligence:
    """Get the global Orca instance."""
    global _orca_instance
    if _orca_instance is None:
        _orca_instance = OrcaKillerWhaleIntelligence()
    return _orca_instance


# ═══════════════════════════════════════════════════════════════════════════════
# TEST / DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🦈🔪 ORCA KILLER WHALE INTELLIGENCE TEST 🔪🦈")
    print("=" * 60)
    print()
    print("📋 COMMAND HIERARCHY:")
    print("   👑 QUEEN SERO (Level 1) - Supreme Commander")
    print("   ↓")
    print("   🦈 ORCA (Level 2) - Tactical Commander")
    print("   ↓")
    print("   💰 MICRO PROFIT (Level 3) - Executor")
    print()
    print("=" * 60)
    
    orca = get_orca()
    
    # Display hierarchy status
    hierarchy = orca.get_hierarchy_status()
    print(f"\n📊 HIERARCHY STATUS:")
    print(f"   Level: {hierarchy['level']} ({hierarchy['name']})")
    print(f"   Reports to: {hierarchy['reports_to']}")
    print(f"   Commands: {hierarchy['commands']}")
    print(f"   Queen Connected: {'✅' if hierarchy['queen_connected'] else '❌'}")
    print(f"   Micro Profit Connected: {'✅' if hierarchy['micro_profit_connected'] else '❌'}")
    print(f"   Chain Integrity: {'✅ COMPLETE' if hierarchy['chain_integrity'] else '⚠️ PARTIAL'}")
    
    # Simulate whale alert
    whale_data = {
        'symbol': 'BTC/USD',
        'side': 'buy',
        'volume_usd': 2_500_000,
        'firm': 'Citadel Securities',
        'firm_confidence': 0.85,
        'exchange': 'kraken'
    }
    
    signal = orca.ingest_whale_alert(whale_data)
    print(f"\n📊 Whale Signal Ingested: {whale_data['symbol']} ${whale_data['volume_usd']:,.0f}")
    
    # Simulate harmonic data
    orca.ingest_harmonic_data({
        'schumann': 0.85,
        'phi': 0.72,
        'love': 0.65,
        'coherence': 0.74
    })
    
    # Simulate fear/greed
    orca.ingest_fear_greed(28)  # Fear
    
    # Scan for opportunities (includes Queen consultation if connected)
    print("\n🔍 Scanning for opportunities (with Queen consultation)...")
    opportunities = orca.scan_for_opportunities()
    
    for opp in opportunities:
        print(f"\n🎯 OPPORTUNITY: {opp.id}")
        print(f"   Symbol: {opp.symbol}")
        print(f"   Action: {opp.action.upper()}")
        print(f"   Confidence: {opp.confidence:.0%}")
        print(f"   Position Size: {opp.position_size_pct:.1%}")
        print(f"   Target PnL: ${opp.target_pnl_usd:.2f}")
        print("   Reasoning (Chain of Command):")
        for r in opp.reasoning:
            print(f"      • {r}")
    
    # Test hierarchy consultation
    if opportunities:
        opp = opportunities[0]
        print(f"\n🧪 TESTING HIERARCHY CONSULTATION:")
        
        # Should consult queen?
        needs_queen = orca.should_consult_queen(opp)
        print(f"   Needs Queen consultation: {'YES' if needs_queen else 'NO'}")
        
        # Consult Queen (will auto-approve if not connected)
        approved, reason, conf = orca.consult_queen(opp)
        print(f"   Queen response: {'APPROVED ✅' if approved else 'VETOED ❌'}")
        print(f"   Reason: {reason}")
        print(f"   Queen confidence: {conf:.0%}")
    
    status = orca.get_status()
    print(f"\n📊 FINAL ORCA STATUS:")
    print(f"   Mode: {status['mode']}")
    print(f"   Hunt Count: {status['hunt_count']}")
    print(f"   Win Rate: {status['win_rate']:.0%}")
    print(f"   Chain Integrity: {'✅' if status['hierarchy']['chain_integrity'] else '⚠️'}")
    print(f"   Queen Approval Rate: {status['hierarchy']['queen_approval_rate']:.0%}")
    
    print("\n🦈 THE KILLER WHALE IS READY TO HUNT! 🦈")
    print("👑→🦈→💰 CHAIN OF COMMAND ESTABLISHED!")
