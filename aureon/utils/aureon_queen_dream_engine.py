#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     👑🔮 AUREON QUEEN'S DREAM ENGINE 🔮👑                                            ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                    ║
║                                                                                      ║
║     THE UNIFIED SIMULATION-VALIDATION-EXECUTION PIPELINE                             ║
║                                                                                      ║
║     ARCHITECTURE:                                                                    ║
║       ┌─────────────────────────────────────────────────────────────┐               ║
║       │  PHASE 1: HISTORICAL ANALYSIS (7-Day Backward)              │               ║
║       │    • Load 7 days of candles per symbol                      │               ║
║       │    • Calculate momentum, volatility, patterns               │               ║
║       └─────────────────────┬───────────────────────────────────────┘               ║
║                             ▼                                                        ║
║       ┌─────────────────────────────────────────────────────────────┐               ║
║       │  PHASE 2: MONTE CARLO SIMULATION (1000+ Paths)              │               ║
║       │    • Simulate 1000 possible futures per opportunity         │               ║
║       │    • Calculate win probability, expected value              │               ║
║       └─────────────────────┬───────────────────────────────────────┘               ║
║                             ▼                                                        ║
║       ┌─────────────────────────────────────────────────────────────┐               ║
║       │  PHASE 3: PREDICTION GENERATION (7-Day Forward)             │               ║
║       │    • Generate price predictions at 1h, 4h, 24h, 7d          │               ║
║       │    • Calculate confidence intervals                         │               ║
║       └─────────────────────┬───────────────────────────────────────┘               ║
║                             ▼                                                        ║
║       ┌─────────────────────────────────────────────────────────────┐               ║
║       │  PHASE 4: LIVE VALIDATION (Real-Time Tickers)               │               ║
║       │    • Compare predictions against incoming tickers           │               ║
║       │    • Track prediction accuracy per symbol                   │               ║
║       │    • Only VALIDATED predictions proceed to execution        │               ║
║       └─────────────────────┬───────────────────────────────────────┘               ║
║                             ▼                                                        ║
║       ┌─────────────────────────────────────────────────────────────┐               ║
║       │  PHASE 5: FASTEST REVENUE SELECTION                         │               ║
║       │    • Rank opportunities by: EV × Confidence × Speed         │               ║
║       │    • Execute ONLY top validated opportunities               │               ║
║       └─────────────────────────────────────────────────────────────┘               ║
║                                                                                      ║
║     Gary Leckey & GitHub Copilot | January 2026                                     ║
║     "Dreams become reality when validated by truth"                                 ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
# Stem → Spore phase aliases for the mushroom branching metaphor
PHASE_ALIAS = {
    "STEM_GATHERING": "PHASE 1: HISTORICAL ANALYSIS (7-Day Backward)",
    "SPORULATION": "PHASE 2: MONTE CARLO SIMULATION (1000+ Paths)",
    "SPORE_PROJECTION": "PHASE 3: PREDICTION GENERATION (7-Day Forward)",
    "GERMINATION_MONITORING": "PHASE 4: LIVE VALIDATION (Real-Time Tickers)",
    "FRUITING": "PHASE 5: FASTEST REVENUE SELECTION",
}

import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import math
import time
import json
import logging
import random
import hashlib
import threading
import statistics
import requests
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from collections import deque, defaultdict
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# � IMPORT MICRO-MOMENTUM GOAL SCANNER
# ═══════════════════════════════════════════════════════════════

try:
    from aureon.conversion.aureon_micro_momentum_goal import MicroMomentumScanner, MomentumTier, MomentumSignal
    MICRO_MOMENTUM_AVAILABLE = True
except ImportError:
    MICRO_MOMENTUM_AVAILABLE = False
    logger.warning("MicroMomentumScanner not available - using fallback")

# ═══════════════════════════════════════════════════════════════
# �🌍 SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528

# ═══════════════════════════════════════════════════════════════
# ⏱️ 30-SECOND TURBO CYCLE TARGET - FASTEST PATH TO REVENUE
# ═══════════════════════════════════════════════════════════════
# The MAIN OBJECTIVE: Complete a full validated cycle in 30 seconds
# This is the FASTEST path to revenue - validated opportunities only!
#
# ⚠️ DEATH BY 1000 CUTS PROTECTION ⚠️
# ALL COSTS MUST BE ACCOUNTED FOR - WE CANNOT BLEED!
#
# REALITY CHECK (based on actual BTC volatility analysis):
# - Hourly volatility: ~0.36%
# - 30-second volatility (scaled): ~0.033%
# - Typical 30-second move: ~0.05%
#
# ═══════════════════════════════════════════════════════════════
# 💸 FULL COST ACCOUNTING - NO HIDDEN BLEED 💸
# ═══════════════════════════════════════════════════════════════

# Trading Fees (per trade, one-way)
FEE_ALPACA_CRYPTO = 0.0015      # 0.15% Alpaca crypto fee
FEE_KRAKEN_TAKER = 0.0026       # 0.26% Kraken taker fee
FEE_KRAKEN_MAKER = 0.0016       # 0.16% Kraken maker fee
FEE_BINANCE_TAKER = 0.001       # 0.10% Binance taker fee

# Spread cost (bid-ask spread, varies by asset)
SPREAD_BTC = 0.0001             # 0.01% BTC spread (liquid)
SPREAD_ETH = 0.0001             # 0.01% ETH spread (liquid)
SPREAD_ALT = 0.0003             # 0.03% altcoin spread (less liquid)

# Slippage (market impact on execution)
SLIPPAGE_SMALL = 0.0001         # 0.01% for < $100 orders
SLIPPAGE_MEDIUM = 0.0003        # 0.03% for $100-$1000 orders
SLIPPAGE_LARGE = 0.001          # 0.10% for > $1000 orders

# ROUND TRIP COST = 2 * (fee + spread/2 + slippage)
# For Alpaca crypto with small orders:
# = 2 * (0.15% + 0.01% + 0.01%) = 0.34% round trip!
#
# This means we need > 0.34% move just to BREAK EVEN!

# Default costs for simulation (Alpaca small crypto orders)
DEFAULT_FEE_ONE_WAY = 0.0015    # 0.15% per trade
DEFAULT_SPREAD = 0.0002         # 0.02% spread (half each way)
DEFAULT_SLIPPAGE = 0.0001       # 0.01% slippage
ROUND_TRIP_COST = 2 * (DEFAULT_FEE_ONE_WAY + DEFAULT_SPREAD/2 + DEFAULT_SLIPPAGE)  # ~0.34%

# Exchange-specific cost profiles (for optimization)
COST_PROFILES = {
    'alpaca': {
        'fee_one_way': 0.0015,  # 0.15%
        'spread': 0.0002,
        'slippage': 0.0001,
        'round_trip': 0.0034  # 0.34%
    },
    'kraken_maker': {
        'fee_one_way': 0.0016,  # 0.16%
        'spread': 0.0001,
        'slippage': 0.0001,
        'round_trip': 0.0036  # 0.36%
    },
    'kraken_taker': {
        'fee_one_way': 0.0026,  # 0.26%
        'spread': 0.0001,
        'slippage': 0.0001,
        'round_trip': 0.0056  # 0.56%
    },
    'binance': {
        'fee_one_way': 0.001,  # 0.10%
        'spread': 0.0001,
        'slippage': 0.0001,
        'round_trip': 0.0024  # 0.24%
    }
}

# ═══════════════════════════════════════════════════════════════
# 📊 MINIMUM PROFITABLE TIMEFRAME CALCULATOR
# ═══════════════════════════════════════════════════════════════
# Based on: volatility scales with sqrt(time)
# BTC hourly vol ~0.36%, so:
#   30-second vol = 0.36% / sqrt(120) = 0.033%
#   5-minute vol = 0.36% / sqrt(12) = 0.104%
#   1-hour vol = 0.36%
#
# To break even with 0.34% cost, we need:
#   Required move = 0.34%
#   At 1.5 sigma (70% confidence), hourly vol gives ~0.54% move
#   Time needed = (0.34 / 0.54)^2 * 3600 = ~1420 seconds = ~24 minutes
#
# MINIMUM PROFITABLE CYCLE for Alpaca: ~30 MINUTES (not 30 seconds!)
# ═══════════════════════════════════════════════════════════════

def calculate_min_profitable_timeframe(hourly_volatility: float, round_trip_cost: float) -> int:
    """
    Calculate the minimum timeframe (in seconds) needed to have a 
    reasonable chance of covering trading costs.
    
    Args:
        hourly_volatility: Standard deviation of hourly returns (e.g., 0.0036 for 0.36%)
        round_trip_cost: Total cost per trade (e.g., 0.0034 for 0.34%)
    
    Returns:
        Minimum seconds needed for expected move to exceed cost
    """
    if hourly_volatility <= 0:
        return 86400  # Default to 1 day if no volatility data
    
    # At 1.5 sigma, we have ~70% chance of moving this much
    sigma_factor = 1.5
    hourly_expected_move = hourly_volatility * sigma_factor
    
    # Time scales with square of ratio
    # vol(t) = vol(hour) * sqrt(t/3600)
    # We need vol(t) * sigma_factor >= cost
    # So: hourly_vol * sqrt(t/3600) * sigma_factor >= cost
    # Solving for t: t >= 3600 * (cost / (hourly_vol * sigma_factor))^2
    
    ratio = round_trip_cost / (hourly_volatility * sigma_factor)
    min_seconds = int(3600 * ratio * ratio)
    
    return max(60, min_seconds)  # At least 1 minute


# ═══════════════════════════════════════════════════════════════

TARGET_CYCLE_SECONDS = 30        # 🎯 GOAL: Full cycle in 30 seconds
TARGET_PROFIT_PER_CYCLE = 0.025  # Target 0.025% per cycle (achievable!)
CYCLES_PER_MINUTE = 2            # 2 cycles per minute
CYCLES_PER_HOUR = 120            # 120 cycles per hour
TARGET_HOURLY_RATE = 3.0         # 0.025% * 120 = 3%/hour potential

# Monte Carlo settings
DEFAULT_SIMULATIONS = 1000
MIN_SIMULATIONS = 100
MAX_SIMULATIONS = 10000

# TURBO simulations for 30-second decisions
TURBO_SIMULATIONS = 200          # More sims for statistical confidence
TURBO_HORIZON_SECONDS = 30       # Simulate 30-second price movements

# Validation thresholds - CALIBRATED for micro-profit
MIN_WIN_PROBABILITY = 0.50  # 50% win rate minimum (need positive EV)
MIN_EXPECTED_VALUE = -0.01  # Allow small negative EV (noise), focus on win rate
MIN_PREDICTION_ACCURACY = 0.5  # 50% direction accuracy

# Time horizons (seconds)
HORIZON_30S = 30            # ⚡ TURBO: 30-second cycle
HORIZON_1M = 60             # 1-minute quick scan
HORIZON_5M = 300            # 5-minute validation
HORIZON_1H = 3600
HORIZON_4H = 14400
HORIZON_24H = 86400
HORIZON_7D = 604800


def _deterministic_standard_normal(path_index: int, step_index: int, path_count: int) -> float:
    """Return a reproducible scenario-grid shock, never a claimed observation."""
    denominator = max(2, path_count * 2)
    sequence_index = (path_index * 104729 + step_index * 13007) % denominator
    quantile = (sequence_index + 0.5) / denominator
    quantile = min(1.0 - 1e-9, max(1e-9, quantile))
    return statistics.NormalDist().inv_cdf(quantile)


# ═══════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class HistoricalCandle:
    """A single OHLCV candle"""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def range_pct(self) -> float:
        """Price range as percentage"""
        if self.open == 0:
            return 0
        return (self.high - self.low) / self.open * 100
    
    @property
    def change_pct(self) -> float:
        """Close vs open as percentage"""
        if self.open == 0:
            return 0
        return (self.close - self.open) / self.open * 100


@dataclass
class SimulationPath:
    """A single Monte Carlo simulation path"""
    path_id: int
    starting_price: float
    ending_price: float
    max_price: float
    min_price: float
    return_pct: float
    max_drawdown_pct: float
    win: bool  # Did it hit profit target?
    time_to_profit_seconds: Optional[float] = None  # If win, how fast?


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation"""
    symbol: str
    num_simulations: int
    
    # Win/Loss stats
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    
    # Return distribution
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0
    min_return: float = 0.0
    max_return: float = 0.0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    expected_value: float = 0.0
    
    # Speed metrics
    avg_time_to_profit: float = 0.0  # Seconds
    fastest_win: float = 0.0
    
    # Confidence
    confidence_95_low: float = 0.0
    confidence_95_high: float = 0.0
    
    # Raw paths for analysis
    paths: List[SimulationPath] = field(default_factory=list)


@dataclass
class PricePrediction:
    """A price prediction at a specific horizon"""
    symbol: str
    created_at: float
    horizon_name: str  # "1h", "4h", "24h", "7d"
    horizon_seconds: int
    target_time: float
    
    # Predictions
    predicted_price: float
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    confidence: float  # 0-1
    confidence_low: float  # 95% CI lower
    confidence_high: float  # 95% CI upper
    
    # Validation (filled after time passes)
    actual_price: Optional[float] = None
    direction_correct: Optional[bool] = None
    price_error_pct: Optional[float] = None
    validated_at: Optional[float] = None


@dataclass
class DreamOpportunity:
    """A fully validated opportunity from the Queen's Dream"""
    dream_id: str
    symbol: str
    exchange: str
    created_at: float
    
    # Historical analysis
    historical_momentum: float
    historical_volatility: float
    historical_win_rate: float
    
    # Monte Carlo results
    simulation_result: SimulationResult
    monte_carlo_win_rate: float
    monte_carlo_ev: float
    
    # Predictions
    predictions: Dict[str, PricePrediction] = field(default_factory=dict)
    
    # Live validation
    validation_count: int = 0
    validation_hits: int = 0
    live_accuracy: float = 0.0
    
    # Final score
    dream_score: float = 0.0  # EV × Confidence × Speed
    revenue_rate: float = 0.0  # Expected $/hour
    
    # Status
    is_validated: bool = False
    is_executed: bool = False
    execution_result: Optional[Dict] = None
    
    def to_stargate_stem_and_spore(self) -> Tuple:
        """
        Convert this dream opportunity into a RealityStem + spore projection data
        for the Stargate Protocol to create timeline branches.
        
        Returns:
            (stem, prediction_data) tuple, or (None, None) if not eligible
        """
        try:
            from aureon.wisdom.aureon_stargate_protocol import RealityStem
            
            # Create the stem (historical data anchor)
            stem = RealityStem(
                stem_id=f"stem::{self.symbol}::{int(self.created_at)}",
                symbol=self.symbol,
                exchange=self.exchange,
                lookback_seconds=HORIZON_7D,  # 7-day historical window
                collected_at=self.created_at,
                notes=f"Dream opportunity {self.dream_id}"
            )
            
            # Create spore projection data
            prediction_data = {
                "symbol": self.symbol,
                "direction": "BULLISH" if self.monte_carlo_ev > 0 else "BEARISH",
                "probability": self.monte_carlo_win_rate,
                "expected_value": self.monte_carlo_ev,
                "confidence": self.live_accuracy if self.validation_count > 0 else self.monte_carlo_win_rate,
                "frequencies": [
                    528.0,  # LOVE frequency (default harmonic)
                    SCHUMANN_BASE * (1 + abs(self.monte_carlo_ev)),  # Scale with EV
                    432.0   # Gaia resonance
                ]
            }
            
            return (stem, prediction_data)
            
        except ImportError:
            return (None, None)


# ═══════════════════════════════════════════════════════════════
# 👑🔮 QUEEN'S DREAM ENGINE
# ═══════════════════════════════════════════════════════════════

class QueenDreamEngine:
    """
    The Queen's Dream Engine - Unified Simulation-Validation-Execution Pipeline
    
    Runs 1000s of simulations, validates predictions against live data,
    and only executes the fastest revenue opportunities.
    
    🎯 THE GOAL: Find coins with EXISTING momentum > 0.34% (trading cost)
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or os.environ.get('ALPACA_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('ALPACA_SECRET_KEY', '')
        self.base_url = 'https://api.alpaca.markets'
        self.data_url = 'https://data.alpaca.markets'
        
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }
        
        # Historical data cache (7-day lookback)
        self._candle_cache: Dict[str, List[HistoricalCandle]] = {}
        self._cache_expiry: Dict[str, float] = {}
        
        # Prediction tracking
        self._pending_predictions: Dict[str, PricePrediction] = {}
        self._validated_predictions: List[PricePrediction] = []
        self._prediction_accuracy: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Dream opportunities
        self._dreams: Dict[str, DreamOpportunity] = {}
        self._validated_dreams: List[DreamOpportunity] = []
        
        # Performance stats
        self.total_simulations_run = 0
        self.total_predictions_made = 0
        self.total_validations = 0
        self.validation_accuracy = 0.0
        
        # 🎯 Micro-Momentum Scanner (THE GOAL!)
        self.momentum_scanner = None
        if MICRO_MOMENTUM_AVAILABLE:
            self.momentum_scanner = MicroMomentumScanner()
            logger.info("🎯 MicroMomentumScanner integrated - THE GOAL is set!")
        
        # 🌌 Stargate Protocol integration
        self.stargate_engine = None
        try:
            from aureon.wisdom.aureon_stargate_protocol import create_stargate_engine
            self.stargate_engine = create_stargate_engine(with_integrations=False)
            logger.info("🌌 Stargate Protocol integrated - spore projection enabled!")
        except ImportError:
            logger.warning("⚠️ Stargate Protocol not available - spore projection disabled")
        
        logger.info("👑🔮 Queen's Dream Engine awakened")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: HISTORICAL ANALYSIS (7-Day Backward)
    # ═══════════════════════════════════════════════════════════════
    
    def scan_for_momentum_first(self) -> List:
        """
        🎯 THE GOAL: Find coins with EXISTING momentum BEFORE simulating!
        
        Only waste simulation time on coins that are ALREADY moving > 0.34%
        """
        if not self.momentum_scanner:
            logger.warning("MicroMomentumScanner not available")
            return []
        
        signals = self.momentum_scanner.get_actionable_signals()
        
        if signals:
            logger.info(f"🎯 Found {len(signals)} coins with momentum > {ROUND_TRIP_COST*100:.2f}%")
            for sig in signals:
                logger.info(f"   {sig.tier.value} {sig.symbol}: {sig.momentum_5m_pct:+.3f}% (net: {sig.net_profit_potential:+.3f}%)")
        else:
            logger.info("⏳ No coins currently moving > cost threshold - waiting...")
        
        return signals
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: HISTORICAL ANALYSIS (7-Day Backward)
    # ═══════════════════════════════════════════════════════════════
    
    def _fetch_historical_candles(self, symbol: str, days: int = 7) -> List[HistoricalCandle]:
        """
        Fetch 7 days of 1-minute candles for a symbol.
        Uses caching to avoid API spam.
        """
        cache_key = f"{symbol}_{days}d"
        
        # Check cache (valid for 5 minutes)
        if cache_key in self._candle_cache:
            if time.time() - self._cache_expiry.get(cache_key, 0) < 300:
                return self._candle_cache[cache_key]
        
        candles = []
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=days)
            
            # Alpaca bars endpoint
            resp = requests.get(
                f'{self.data_url}/v1beta3/crypto/us/bars',
                headers=self.headers,
                params={
                    'symbols': f'{symbol}/USD',
                    'timeframe': '1Hour',  # Hourly for 7-day analysis
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                    'limit': 10000
                },
                timeout=10
            )
            
            data = resp.json()
            bars = data.get('bars', {}).get(f'{symbol}/USD', [])
            
            for bar in bars:
                candles.append(HistoricalCandle(
                    timestamp=datetime.fromisoformat(bar['t'].replace('Z', '+00:00')).timestamp(),
                    open=float(bar['o']),
                    high=float(bar['h']),
                    low=float(bar['l']),
                    close=float(bar['c']),
                    volume=float(bar['v'])
                ))
            
            # Cache it
            self._candle_cache[cache_key] = candles
            self._cache_expiry[cache_key] = time.time()
            
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
        
        return candles
    
    def _analyze_historical(self, symbol: str) -> Dict[str, float]:
        """
        Analyze 7 days of historical data.
        Returns momentum, volatility, win rate, etc.
        """
        candles = self._fetch_historical_candles(symbol, days=7)
        
        if len(candles) < 24:  # Need at least 24 hours
            return {
                'momentum': None,
                'volatility': None,
                'win_rate': None,
                'avg_move': None,
                'trend': None,
                'candle_count': len(candles),
                'truth_status': 'no_data',
            }
        
        # Calculate returns
        returns = []
        for i in range(1, len(candles)):
            ret = (candles[i].close - candles[i-1].close) / candles[i-1].close
            returns.append(ret)
        
        # Momentum: Recent vs older performance
        recent_returns = returns[-24:]  # Last 24 hours
        older_returns = returns[:-24] if len(returns) > 24 else returns
        
        recent_mean = statistics.mean(recent_returns) if recent_returns else 0
        older_mean = statistics.mean(older_returns) if older_returns else 0
        
        momentum = recent_mean - older_mean
        
        # Volatility: Standard deviation of returns
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0
        
        # Win rate: % of positive candles
        wins = sum(1 for r in returns if r > 0)
        win_rate = wins / len(returns) if returns else 0.5
        
        # Average move
        avg_move = statistics.mean([abs(r) for r in returns]) if returns else 0
        
        # Trend: Linear regression slope
        if len(candles) >= 2:
            prices = [c.close for c in candles]
            x = list(range(len(prices)))
            n = len(prices)
            slope = (n * sum(x[i] * prices[i] for i in range(n)) - sum(x) * sum(prices)) / \
                    (n * sum(xi**2 for xi in x) - sum(x)**2) if n > 1 else 0
            trend = slope / prices[-1] if prices[-1] else 0  # Normalize by current price
        else:
            trend = 0
        
        return {
            'momentum': momentum,
            'volatility': volatility,
            'win_rate': win_rate,
            'avg_move': avg_move,
            'trend': trend,
            'candle_count': len(candles)
        }
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: MONTE CARLO SIMULATION (1000+ Paths)
    # ═══════════════════════════════════════════════════════════════
    
    def run_monte_carlo(self, symbol: str, current_price: float,
                        profit_target_pct: float = 0.5,
                        stop_loss_pct: float = 1.0,
                        horizon_hours: int = 24,
                        num_simulations: int = DEFAULT_SIMULATIONS) -> SimulationResult:
        """
        Run Monte Carlo simulation for a symbol.
        
        Uses historical volatility and drift to simulate 1000+ possible futures.
        Returns win rate, expected value, and speed metrics.
        """
        # Get historical stats for calibration
        hist = self._analyze_historical(symbol)
        if hist.get('truth_status') == 'no_data' or hist.get('candle_count', 0) < 24:
            raise RuntimeError(f"NO_FRESH_HISTORICAL_CANDLES:{symbol}")
        
        # Calibration from historical data
        hourly_drift = hist['momentum'] / 24  # Per-hour drift
        hourly_vol = hist['volatility'] / math.sqrt(24)  # Per-hour volatility
        
        # Ensure reasonable bounds
        hourly_drift = max(-0.01, min(0.01, hourly_drift))  # Cap at ±1%/hour
        hourly_vol = max(0.001, min(0.05, hourly_vol))  # Between 0.1% and 5%/hour
        
        # Run simulations
        paths = []
        wins = 0
        times_to_profit = []
        
        for i in range(num_simulations):
            # Simulate price path
            price = current_price
            max_price = price
            min_price = price
            
            hit_profit = False
            hit_stop = False
            time_to_profit = None
            
            for hour in range(horizon_hours):
                # Geometric Brownian Motion step
                scenario_shock = _deterministic_standard_normal(i, hour, num_simulations)
                pct_change = hourly_drift + hourly_vol * scenario_shock
                price = price * (1 + pct_change)
                
                max_price = max(max_price, price)
                min_price = min(min_price, price)
                
                # Check profit target
                gain_pct = (price - current_price) / current_price * 100
                if not hit_profit and gain_pct >= profit_target_pct:
                    hit_profit = True
                    time_to_profit = (hour + 1) * 3600  # Seconds
                
                # Check stop loss
                if gain_pct <= -stop_loss_pct:
                    hit_stop = True
                    break
            
            # Record path
            final_return = (price - current_price) / current_price * 100
            max_dd = (current_price - min_price) / current_price * 100
            
            path = SimulationPath(
                path_id=i,
                starting_price=current_price,
                ending_price=price,
                max_price=max_price,
                min_price=min_price,
                return_pct=final_return,
                max_drawdown_pct=max_dd,
                win=hit_profit and not hit_stop,
                time_to_profit_seconds=time_to_profit
            )
            paths.append(path)
            
            if path.win:
                wins += 1
                if time_to_profit:
                    times_to_profit.append(time_to_profit)
        
        # Calculate statistics
        returns = [p.return_pct for p in paths]
        drawdowns = [p.max_drawdown_pct for p in paths]
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0
        
        # Sharpe ratio (assuming 0 risk-free rate for crypto)
        sharpe = mean_return / std_return if std_return > 0 else 0
        
        # Expected value: mean return adjusted for win rate
        win_rate = wins / num_simulations
        expected_value = (win_rate * profit_target_pct) - ((1 - win_rate) * stop_loss_pct)
        
        # 95% confidence interval
        sorted_returns = sorted(returns)
        ci_low_idx = int(0.025 * len(sorted_returns))
        ci_high_idx = int(0.975 * len(sorted_returns))
        
        result = SimulationResult(
            symbol=symbol,
            num_simulations=num_simulations,
            wins=wins,
            losses=num_simulations - wins,
            win_rate=win_rate,
            mean_return=mean_return,
            median_return=statistics.median(returns),
            std_return=std_return,
            min_return=min(returns),
            max_return=max(returns),
            sharpe_ratio=sharpe,
            max_drawdown=max(drawdowns),
            expected_value=expected_value,
            avg_time_to_profit=statistics.mean(times_to_profit) if times_to_profit else horizon_hours * 3600,
            fastest_win=min(times_to_profit) if times_to_profit else 0,
            confidence_95_low=sorted_returns[ci_low_idx],
            confidence_95_high=sorted_returns[ci_high_idx],
            paths=paths[:10]  # Keep first 10 for analysis
        )
        
        self.total_simulations_run += num_simulations
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # ⚡ TURBO 30-SECOND SIMULATION - FASTEST PATH TO REVENUE
    # ═══════════════════════════════════════════════════════════════
    
    def run_turbo_30s_simulation(self, symbol: str, current_price: float,
                                  profit_target_pct: float = 0.1,
                                  stop_loss_pct: float = 0.2,
                                  num_simulations: int = TURBO_SIMULATIONS) -> SimulationResult:
        """
        ⚡ TURBO 30-SECOND SIMULATION
        
        The MAIN OBJECTIVE: Validate the quickest path to revenue in 30 seconds.
        
        This simulates MICRO price movements over 30 seconds:
        - Uses tick-level volatility (scaled from hourly)
        - Target: 0.1% profit in 30 seconds
        - Goal: 2 cycles per minute = 120 cycles per hour
        
        Args:
            symbol: The crypto symbol
            current_price: Current price
            profit_target_pct: Target profit % (default 0.1%)
            stop_loss_pct: Stop loss % (default 0.2%)
            num_simulations: Number of sims (default 50 for speed)
            
        Returns:
            SimulationResult optimized for 30-second cycles
        """
        # Get historical stats for calibration
        hist = self._analyze_historical(symbol)
        if hist.get('truth_status') == 'no_data' or hist.get('candle_count', 0) < 24:
            raise RuntimeError(f"NO_FRESH_HISTORICAL_CANDLES:{symbol}")
        
        # Scale hourly volatility to 30-second intervals
        # 30 seconds = 1/120 of an hour
        # Volatility scales by sqrt(time)
        # REALITY: BTC hourly vol ~0.36%, so 30-sec vol ~0.033%
        hourly_vol = hist.get('volatility', 0.0036)  # Default 0.36% hourly
        thirty_sec_vol = hourly_vol / math.sqrt(120)  # ~0.00033 for typical crypto
        
        # Drift is very small over 30 seconds
        hourly_drift = hist.get('momentum', 0) / 24
        thirty_sec_drift = hourly_drift / 120
        
        # Ensure reasonable bounds - but don't over-clamp!
        thirty_sec_drift = max(-0.002, min(0.002, thirty_sec_drift))
        thirty_sec_vol = max(0.0001, min(0.01, thirty_sec_vol))  # Allow up to 1% per 30s
        
        # Log for debugging
        candle_count = hist.get('candle_count', 0)
        if candle_count > 0:
            logger.debug(f"{symbol}: hourly_vol={hourly_vol*100:.4f}%, 30s_vol={thirty_sec_vol*100:.6f}%, candles={candle_count}")
        
        # Run simulations - each simulation is ONE 30-second window
        paths = []
        wins = 0
        times_to_profit = []
        total_pnl = 0.0  # Track total PnL across all simulations
        
        for i in range(num_simulations):
            # Simulate 30 one-second ticks
            price = current_price
            max_price = price
            min_price = price
            
            hit_profit = False
            hit_stop = False
            time_to_profit = None
            
            for tick in range(30):  # 30 seconds
                # Random walk with drift
                scenario_shock = _deterministic_standard_normal(i, tick, num_simulations)
                pct_change = thirty_sec_drift + thirty_sec_vol * scenario_shock
                price = price * (1 + pct_change)
                
                max_price = max(max_price, price)
                min_price = min(min_price, price)
                
                # Check profit target (GROSS, before costs)
                gross_gain_pct = (price - current_price) / current_price * 100
                if not hit_profit and gross_gain_pct >= profit_target_pct:
                    hit_profit = True
                    time_to_profit = tick + 1  # Seconds to profit
                
                # Check stop loss (wide to avoid premature exit)
                if gross_gain_pct <= -stop_loss_pct:
                    hit_stop = True
                    break
            
            # ═══════════════════════════════════════════════════════════════
            # 💸 COST ACCOUNTING - SUBTRACT ALL TRADING COSTS 💸
            # ═══════════════════════════════════════════════════════════════
            
            # GROSS return (before costs)
            gross_return = (price - current_price) / current_price * 100
            
            # COSTS (as percentage)
            # Round trip = entry fee + exit fee + spread + slippage
            cost_pct = ROUND_TRIP_COST * 100  # Convert to percentage (~0.34%)
            
            # NET return (after ALL costs)
            net_return = gross_return - cost_pct
            
            max_dd = (current_price - min_price) / current_price * 100
            
            # Win = NET return is positive (after costs!)
            # This is the REAL test - did we make money after fees?
            net_win = net_return > 0
            
            path = SimulationPath(
                path_id=i,
                starting_price=current_price,
                ending_price=price,
                max_price=max_price,
                min_price=min_price,
                return_pct=net_return,  # Store NET return, not gross!
                max_drawdown_pct=max_dd,
                win=net_win,  # Win only if NET positive
                time_to_profit_seconds=time_to_profit
            )
            paths.append(path)
            total_pnl += net_return  # Accumulate NET returns
            
            if path.win:
                wins += 1
                if time_to_profit:
                    times_to_profit.append(time_to_profit)
        
        # Calculate statistics (all using NET returns)
        returns = [p.return_pct for p in paths]  # These are NET returns
        drawdowns = [p.max_drawdown_pct for p in paths]
        
        mean_return = statistics.mean(returns) if returns else 0
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0
        
        win_rate = wins / num_simulations
        
        # EV is the mean NET return (after all costs)
        expected_value = mean_return  # This is NET EV
        
        # Revenue rate calculation for 30-second cycles
        revenue_per_cycle = expected_value / 100  # As decimal
        cycles_per_hour = 120  # 30-second cycles
        revenue_rate_hourly = revenue_per_cycle * cycles_per_hour * 100  # As percentage per hour
        
        # 95% confidence interval
        sorted_returns = sorted(returns)
        ci_low_idx = max(0, int(0.025 * len(sorted_returns)))
        ci_high_idx = min(len(sorted_returns) - 1, int(0.975 * len(sorted_returns)))
        
        result = SimulationResult(
            symbol=symbol,
            num_simulations=num_simulations,
            wins=wins,
            losses=num_simulations - wins,
            win_rate=win_rate,
            mean_return=mean_return,
            median_return=statistics.median(returns) if returns else 0,
            std_return=std_return,
            min_return=min(returns) if returns else 0,
            max_return=max(returns) if returns else 0,
            sharpe_ratio=mean_return / std_return if std_return > 0 else 0,
            max_drawdown=max(drawdowns) if drawdowns else 0,
            expected_value=expected_value,
            avg_time_to_profit=statistics.mean(times_to_profit) if times_to_profit else 30,
            fastest_win=min(times_to_profit) if times_to_profit else 0,
            confidence_95_low=sorted_returns[ci_low_idx] if sorted_returns else 0,
            confidence_95_high=sorted_returns[ci_high_idx] if sorted_returns else 0,
            paths=paths[:10]
        )
        
        self.total_simulations_run += num_simulations
        return result
    
    def find_fastest_30s_opportunity(self, symbols: List[str] = None,
                                      current_prices: Dict[str, float] = None) -> Optional[Dict]:
        """
        🎯 MAIN OBJECTIVE: Find the FASTEST validated path to revenue in 30 seconds.
        
        Scans all symbols with TURBO simulation and returns the BEST opportunity
        that can complete a full profitable cycle in 30 seconds.
        
        Returns:
            Dict with best opportunity details, or None if none found
        """
        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL', 'LINK', 'DOGE', 'XRP', 'AVAX']
        
        if current_prices is None:
            current_prices = {}
        
        best_opportunity = None
        best_score = -999
        
        print(f"\n⚡ TURBO 30-SECOND SCAN - Finding fastest path to revenue...")
        print(f"   Target: {TARGET_PROFIT_PER_CYCLE}% gross profit per 30-second cycle")
        print(f"   Goal: {CYCLES_PER_HOUR} cycles/hour = ${TARGET_HOURLY_RATE}/hour potential")
        print("")
        print(f"   💸 COST ACCOUNTING (per round trip):")
        print(f"      Fee (entry+exit): {DEFAULT_FEE_ONE_WAY*2*100:.3f}%")
        print(f"      Spread:           {DEFAULT_SPREAD*100:.3f}%")
        print(f"      Slippage:         {DEFAULT_SLIPPAGE*2*100:.3f}%")
        print(f"      ─────────────────────────")
        print(f"      TOTAL COST:       {ROUND_TRIP_COST*100:.3f}% per trade")
        print(f"      Break-even move:  {ROUND_TRIP_COST*100:.3f}%")
        print("-" * 60)
        
        for symbol in symbols:
            price = current_prices.get(symbol, 0)
            if price <= 0:
                # Try to get price
                try:
                    resp = requests.get(
                        f'{self.data_url}/v1beta3/crypto/us/latest/trades?symbols={symbol}/USD',
                        headers=self.headers, timeout=3
                    )
                    trades = resp.json().get('trades', {}).get(f'{symbol}/USD', [])
                    if trades:
                        price = float(trades[-1]['p'])
                except:
                    continue
            
            if price <= 0:
                continue
            
            # Run TURBO 30-second simulation
            # For micro-scalping: no hard stop, exit at time limit
            # Target = 0.025%, Stop = None (time-based exit at 30s)
            result = self.run_turbo_30s_simulation(
                symbol=symbol,
                current_price=price,
                profit_target_pct=TARGET_PROFIT_PER_CYCLE,
                stop_loss_pct=TARGET_PROFIT_PER_CYCLE * 3,  # Wide stop (3x profit target)
                num_simulations=TURBO_SIMULATIONS
            )
            
            # Score = (EV + offset) * speed_factor
            # For micro-scalping, POSITIVE EV IS KING - win rate matters less
            # Because we exit at time limit, not fixed target
            speed_factor = 30 / max(1, result.avg_time_to_profit)  # Faster = better
            ev_score = result.expected_value + 0.05  # Offset so positive EV scores higher
            score = ev_score * speed_factor
            
            # VALIDATION: Positive EV is the key metric for time-based exits
            is_valid = result.expected_value > 0.001  # >0.001% actual positive EV
            status = "✅" if is_valid else "❌"
            print(f"   {symbol:6s} | Win: {result.win_rate*100:5.1f}% | "
                  f"EV: {result.expected_value:+.4f}% | "
                  f"Avg: {result.avg_time_to_profit:.1f}s | {status}")
            
            # Accept if EV is positive (for time-based exit strategy)
            if score > best_score and is_valid:
                best_score = score
                best_opportunity = {
                    'symbol': symbol,
                    'price': price,
                    'win_rate': result.win_rate,
                    'expected_value': result.expected_value,
                    'avg_time_to_profit': result.avg_time_to_profit,
                    'fastest_win': result.fastest_win,
                    'score': score,
                    'cycles_per_hour': 3600 / max(1, result.avg_time_to_profit),
                    'revenue_rate_pct_hour': result.expected_value * (3600 / max(1, result.avg_time_to_profit))
                }
        
        print("-" * 60)
        
        if best_opportunity:
            print(f"\n🎯 FASTEST PATH TO REVENUE:")
            print(f"   Symbol: {best_opportunity['symbol']}")
            print(f"   Win Rate: {best_opportunity['win_rate']*100:.1f}%")
            print(f"   Expected Value: {best_opportunity['expected_value']:+.4f}% per cycle")
            print(f"   Avg Time to Profit: {best_opportunity['avg_time_to_profit']:.1f} seconds")
            print(f"   Cycles per Hour: {best_opportunity['cycles_per_hour']:.0f}")
            print(f"   Revenue Rate: {best_opportunity['revenue_rate_pct_hour']:.2f}%/hour")
        else:
            print("\n⚠️ No validated 30-second opportunities found")
        
        return best_opportunity
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: PREDICTION GENERATION (7-Day Forward)
    # ═══════════════════════════════════════════════════════════════
    
    def generate_predictions(self, symbol: str, current_price: float,
                            simulation_result: SimulationResult) -> Dict[str, PricePrediction]:
        """
        Generate price predictions at multiple horizons.
        Uses Monte Carlo results to set confidence intervals.
        """
        now = time.time()
        predictions = {}
        
        horizons = [
            ("1h", HORIZON_1H),
            ("4h", HORIZON_4H),
            ("24h", HORIZON_24H),
            ("7d", HORIZON_7D)
        ]
        
        for name, seconds in horizons:
            # Scale simulation results to this horizon
            horizon_factor = seconds / (24 * 3600)  # Relative to 24h simulation
            
            # Predicted price based on mean return
            predicted_return = simulation_result.mean_return * horizon_factor
            predicted_price = current_price * (1 + predicted_return / 100)
            
            # Confidence interval (scaled by sqrt of time)
            ci_factor = math.sqrt(horizon_factor)
            ci_low = current_price * (1 + simulation_result.confidence_95_low * ci_factor / 100)
            ci_high = current_price * (1 + simulation_result.confidence_95_high * ci_factor / 100)
            
            # Direction prediction
            if predicted_return > 0.1:
                direction = "UP"
            elif predicted_return < -0.1:
                direction = "DOWN"
            else:
                direction = "FLAT"
            
            # Confidence based on historical accuracy + simulation coherence
            hist_accuracy = self._get_symbol_accuracy(symbol)
            sim_coherence = 1 - (simulation_result.std_return / 10)  # Lower std = higher coherence
            confidence = (hist_accuracy + max(0, sim_coherence)) / 2
            
            prediction = PricePrediction(
                symbol=symbol,
                created_at=now,
                horizon_name=name,
                horizon_seconds=seconds,
                target_time=now + seconds,
                predicted_price=predicted_price,
                predicted_direction=direction,
                confidence=confidence,
                confidence_low=ci_low,
                confidence_high=ci_high
            )
            
            predictions[name] = prediction
            
            # Store for validation tracking
            pred_id = f"{symbol}_{name}_{int(now)}"
            self._pending_predictions[pred_id] = prediction
            self.total_predictions_made += 1
        
        return predictions
    
    def _get_symbol_accuracy(self, symbol: str) -> float:
        """Get historical prediction accuracy for a symbol"""
        history = self._prediction_accuracy.get(symbol, deque())
        if len(history) < 5:
            return 0.5  # Default 50% if not enough history
        return sum(history) / len(history)
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: LIVE VALIDATION (Real-Time Tickers)
    # ═══════════════════════════════════════════════════════════════
    
    def validate_predictions_with_ticker(self, symbol: str, live_price: float) -> List[PricePrediction]:
        """
        Validate pending predictions against live ticker data.
        Called when new price data arrives.
        """
        now = time.time()
        validated = []
        
        # Find predictions that are due for validation
        to_remove = []
        for pred_id, prediction in self._pending_predictions.items():
            if prediction.symbol != symbol:
                continue
            
            # Check if target time has passed
            if now >= prediction.target_time:
                # Validate!
                prediction.actual_price = live_price
                prediction.validated_at = now
                
                # Direction correctness
                actual_direction = "UP" if live_price > prediction.predicted_price * 0.999 else \
                                  "DOWN" if live_price < prediction.predicted_price * 1.001 else "FLAT"
                prediction.direction_correct = (prediction.predicted_direction == actual_direction) or \
                                               (prediction.predicted_direction != "FLAT" and 
                                                ((prediction.predicted_direction == "UP" and live_price > prediction.predicted_price * 0.99) or
                                                 (prediction.predicted_direction == "DOWN" and live_price < prediction.predicted_price * 1.01)))
                
                # Price error
                prediction.price_error_pct = abs(live_price - prediction.predicted_price) / prediction.predicted_price * 100
                
                # Update accuracy tracking
                self._prediction_accuracy[symbol].append(1.0 if prediction.direction_correct else 0.0)
                
                validated.append(prediction)
                self._validated_predictions.append(prediction)
                to_remove.append(pred_id)
                
                self.total_validations += 1
                
                logger.info(f"🔮 VALIDATED: {symbol} {prediction.horizon_name} | "
                           f"Predicted: ${prediction.predicted_price:.2f} | "
                           f"Actual: ${live_price:.2f} | "
                           f"Direction: {'✅' if prediction.direction_correct else '❌'}")
        
        # Clean up validated predictions
        for pred_id in to_remove:
            del self._pending_predictions[pred_id]
        
        # Update overall accuracy
        if self._validated_predictions:
            correct = sum(1 for p in self._validated_predictions[-100:] if p.direction_correct)
            self.validation_accuracy = correct / min(100, len(self._validated_predictions))
        
        return validated
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: DREAM CREATION & FASTEST REVENUE SELECTION
    # ═══════════════════════════════════════════════════════════════
    
    def create_dream(self, symbol: str, exchange: str = 'alpaca',
                    num_simulations: int = DEFAULT_SIMULATIONS,
                    current_price: float = None) -> Optional[DreamOpportunity]:
        """
        Create a full Dream Opportunity:
        1. Analyze history
        2. Run simulations
        3. Generate predictions
        4. Calculate revenue rate
        
        Can accept current_price directly to avoid API call (when called from labyrinth)
        """
        if current_price is None:
            try:
                # Try Alpaca first
                resp = requests.get(
                    f'{self.data_url}/v1beta3/crypto/us/latest/trades?symbols={symbol}/USD',
                    headers=self.headers, timeout=5
                )
                trades = resp.json().get('trades', {}).get(f'{symbol}/USD', [])
                if trades:
                    current_price = float(trades[-1]['p'])
                else:
                    # Fallback to CoinGecko (free, no API key needed)
                    cg_id = symbol.lower()
                    cg_resp = requests.get(
                        f'https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd',
                        timeout=5
                    )
                    cg_data = cg_resp.json()
                    if cg_id in cg_data:
                        current_price = float(cg_data[cg_id]['usd'])
                    else:
                        logger.warning(f"No price found for {symbol}")
                        return None
                    
            except Exception as e:
                logger.error(f"Failed to get price for {symbol}: {e}")
                return None
        
        if not current_price or current_price <= 0:
            return None
        
        # PHASE 1: Historical Analysis
        hist = self._analyze_historical(symbol)
        
        # PHASE 2: Monte Carlo Simulation
        sim_result = self.run_monte_carlo(
            symbol=symbol,
            current_price=current_price,
            profit_target_pct=0.5,  # 0.5% profit target
            stop_loss_pct=1.0,  # 1% stop loss
            horizon_hours=24,
            num_simulations=num_simulations
        )
        
        # PHASE 3: Generate Predictions
        predictions = self.generate_predictions(symbol, current_price, sim_result)
        
        # Calculate Dream Score and Revenue Rate
        # Score = Win Rate × EV × Speed Factor
        speed_factor = 1.0 / max(1, sim_result.avg_time_to_profit / 3600)  # Higher = faster
        dream_score = sim_result.win_rate * sim_result.expected_value * speed_factor
        
        # Revenue Rate = Expected $ per hour (assuming $100 position)
        position_value = 100  # $100 position
        expected_profit = position_value * (sim_result.expected_value / 100)
        hours_to_profit = sim_result.avg_time_to_profit / 3600
        revenue_rate = expected_profit / max(0.1, hours_to_profit)  # $/hour
        
        dream = DreamOpportunity(
            dream_id=hashlib.md5(f"{symbol}_{time.time()}".encode()).hexdigest()[:12],
            symbol=symbol,
            exchange=exchange,
            created_at=time.time(),
            historical_momentum=hist['momentum'],
            historical_volatility=hist['volatility'],
            historical_win_rate=hist['win_rate'],
            simulation_result=sim_result,
            monte_carlo_win_rate=sim_result.win_rate,
            monte_carlo_ev=sim_result.expected_value,
            predictions=predictions,
            dream_score=dream_score,
            revenue_rate=revenue_rate,
            is_validated=sim_result.win_rate >= MIN_WIN_PROBABILITY and sim_result.expected_value >= MIN_EXPECTED_VALUE
        )
        
        self._dreams[dream.dream_id] = dream
        if dream.is_validated:
            self._validated_dreams.append(dream)
        
        # 🍄 PROJECT SPORE TO STARGATE if engine available
        if self.stargate_engine and dream.is_validated:
            stem, prediction_data = dream.to_stargate_stem_and_spore()
            if stem and prediction_data:
                try:
                    spore_mirror = self.stargate_engine.project_spore_from_stem(stem, prediction_data)
                    if spore_mirror:
                        logger.info(f"🍄 Spore projected to Stargate: {spore_mirror.mirror_id}")
                except Exception as e:
                    logger.warning(f"Failed to project spore: {e}")
        
        return dream
    
    def get_fastest_revenue_opportunities(self, limit: int = 5) -> List[DreamOpportunity]:
        """
        Get the TOP opportunities ranked by Revenue Rate.
        Only returns validated dreams.
        """
        # Filter to validated dreams
        valid = [d for d in self._dreams.values() 
                 if d.is_validated and not d.is_executed]
        
        # Sort by revenue rate ($/hour)
        valid.sort(key=lambda d: d.revenue_rate, reverse=True)
        
        return valid[:limit]
    
    def scan_and_rank_all(self, symbols: List[str] = None,
                          num_simulations: int = DEFAULT_SIMULATIONS) -> List[DreamOpportunity]:
        """
        Full scan: Analyze all symbols and return ranked opportunities.
        This is the main entry point for the Queen's Dream.
        """
        if symbols is None:
            # Default high-liquidity crypto
            symbols = ['BTC', 'ETH', 'SOL', 'LINK', 'DOGE', 'XRP', 'AVAX', 
                      'UNI', 'AAVE', 'LTC', 'DOT', 'MATIC', 'ATOM', 'CRV']
        
        print("\n" + "=" * 70)
        print("👑🔮 QUEEN'S DREAM ENGINE - FULL SCAN")
        print("=" * 70)
        print(f"   Symbols: {len(symbols)}")
        print(f"   Simulations per symbol: {num_simulations}")
        print(f"   Total simulations: {len(symbols) * num_simulations:,}")
        print("=" * 70 + "\n")
        
        for symbol in symbols:
            try:
                dream = self.create_dream(symbol, num_simulations=num_simulations)
                if dream:
                    status = "✅ VALIDATED" if dream.is_validated else "❌ REJECTED"
                    print(f"{symbol:6s} | Win: {dream.monte_carlo_win_rate*100:5.1f}% | "
                          f"EV: {dream.monte_carlo_ev:+6.3f}% | "
                          f"$/hr: ${dream.revenue_rate:6.2f} | {status}")
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
        
        # Get ranked results
        ranked = self.get_fastest_revenue_opportunities(limit=10)
        
        print("\n" + "=" * 70)
        print("🏆 TOP OPPORTUNITIES BY REVENUE RATE")
        print("=" * 70)
        
        for i, dream in enumerate(ranked, 1):
            print(f"   #{i} {dream.symbol:6s} | "
                  f"${dream.revenue_rate:.2f}/hr | "
                  f"Win: {dream.monte_carlo_win_rate*100:.1f}% | "
                  f"EV: {dream.monte_carlo_ev:+.3f}%")
        
        print("=" * 70)
        print(f"\n📊 STATS: {self.total_simulations_run:,} simulations | "
              f"{self.total_predictions_made} predictions | "
              f"{self.total_validations} validations | "
              f"Accuracy: {self.validation_accuracy*100:.1f}%")
        
        return ranked
    
    def get_dream_summary(self) -> Dict[str, Any]:
        """Get summary of all dreams for the Queen"""
        return {
            'total_dreams': len(self._dreams),
            'validated_dreams': len(self._validated_dreams),
            'total_simulations': self.total_simulations_run,
            'total_predictions': self.total_predictions_made,
            'total_validations': self.total_validations,
            'validation_accuracy': self.validation_accuracy,
            'top_opportunities': [
                {
                    'symbol': d.symbol,
                    'revenue_rate': d.revenue_rate,
                    'win_rate': d.monte_carlo_win_rate,
                    'ev': d.monte_carlo_ev
                }
                for d in self.get_fastest_revenue_opportunities(5)
            ]
        }


# ═══════════════════════════════════════════════════════════════
# 🌍 FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════

def create_queen_dream_engine() -> QueenDreamEngine:
    """Create and return a Queen's Dream Engine instance"""
    return QueenDreamEngine()


# ═══════════════════════════════════════════════════════════════
# MAIN - TEST THE DREAM
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     👑🔮 QUEEN'S DREAM ENGINE 🔮👑                                           ║
║     "Dreams become reality when validated by truth"                          ║
║                                                                              ║
║     🎯 MAIN OBJECTIVE: 30-SECOND CYCLE TO REVENUE                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    engine = create_queen_dream_engine()
    
    # Check for --turbo flag for 30-second mode
    if '--turbo' in sys.argv or '-t' in sys.argv:
        print("\n⚡ TURBO MODE: 30-SECOND CYCLE VALIDATION")
        print("=" * 60)
        
        # Test with sample prices (bypasses API for demo)
        sample_prices = {
            'BTC': 95000,
            'ETH': 3500,
            'SOL': 200,
            'LINK': 25,
            'DOGE': 0.35,
            'XRP': 2.5,
            'AVAX': 40,
        }
        
        best = engine.find_fastest_30s_opportunity(
            symbols=list(sample_prices.keys()),
            current_prices=sample_prices
        )
        
        if best:
            print(f"\n✅ VALIDATED: Execute {best['symbol']} for fastest revenue!")
        
    else:
        # Default: Run full scan with 1000 simulations per symbol
        print("\n📊 FULL SCAN MODE (use --turbo for 30-second cycles)")
        ranked = engine.scan_and_rank_all(
            symbols=['BTC', 'ETH', 'SOL', 'LINK', 'DOGE', 'AVAX', 'AAVE', 'UNI'],
            num_simulations=1000
        )
    
    print("\n👑 The Queen's Dream has spoken. Execute the validated visions.")
