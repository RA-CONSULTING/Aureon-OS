#!/usr/bin/env python3
"""
🦈🔪⚡ ORCA UNLEASHED - THE KILLER WHALE HUNTS! ⚡🔪🦈
═══════════════════════════════════════════════════════════

NO MORE TINY TRADES!
NO MORE DEATH BY FEES!
NO MORE PHANTOM PROFITS!

THE ORCA WAITS... WATCHES... AND STRIKES WITH PRECISION!

Rules:
1. MINIMUM $5 trade (no more dust!)
2. ONLY trade when confidence > 75%
3. Wait for REAL opportunities (not noise)
4. Take profit at 1-2%, cut losses at 0.5%
5. Maximum 3 trades per hour (quality over quantity)

Gary Leckey | January 2026 | UNLEASH THE BEAST!
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Real portfolio tracker
try:
    from aureon.portfolio.aureon_real_portfolio_tracker import get_real_portfolio_tracker, RealPortfolioSnapshot
    PORTFOLIO_TRACKER_AVAILABLE = True
except ImportError:
    PORTFOLIO_TRACKER_AVAILABLE = False
    get_real_portfolio_tracker = None

# 🔮 PROBABILITY NEXUS - For smart kill decisions!
try:
    from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus, Prediction
    PROBABILITY_NEXUS_AVAILABLE = True
    logger.info("🔮 Probability Nexus CONNECTED - Smart kill decisions enabled!")
except ImportError:
    PROBABILITY_NEXUS_AVAILABLE = False
    AureonProbabilityNexus = None
    Prediction = None

# 🎯 HUNTING GROUNDS - Find best places to hunt!
try:
    from aureon.bots.orca_hunting_grounds import OrcaHuntingGrounds, HuntingGround
    HUNTING_GROUNDS_AVAILABLE = True
    logger.info("🎯 Hunting Grounds CONNECTED - Smart venue selection enabled!")
except ImportError:
    HUNTING_GROUNDS_AVAILABLE = False
    OrcaHuntingGrounds = None
    HuntingGround = None

# Exchange clients
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None


@dataclass
class OrcaHunt:
    """A potential hunting opportunity."""
    symbol: str
    exchange: str
    direction: str  # 'long' or 'short'
    confidence: float
    entry_price: float
    target_price: float
    stop_price: float
    size_usd: float
    reasoning: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class OrcaKill:
    """A completed trade."""
    symbol: str
    exchange: str
    direction: str
    entry_price: float
    exit_price: float
    size_usd: float
    pnl_usd: float
    pnl_pct: float
    duration_seconds: float
    timestamp: float


class OrcaUnleashed:
    """
    🦈🔪⚡ THE UNLEASHED ORCA ⚡🔪🦈
    
    No more tiny trades. No more death by fees.
    The Orca waits for the perfect moment, then STRIKES!
    """
    
    # STRICT RULES - NO EXCEPTIONS!
    # 🔥 TRUTH: Alpaca fees are 0.25% PER SIDE = 0.50% round trip MINIMUM!
    # So we MUST have take profit > 0.50% just to break even!
    MIN_TRADE_SIZE_USD = 5.0       # Minimum $5 per trade (bigger = better fee ratio)
    MIN_CONFIDENCE = 0.70          # 70% confidence minimum 
    MAX_TRADES_PER_HOUR = 3        # FEWER trades = FEWER fees!
    TAKE_PROFIT_PCT = 0.015        # 1.5% take profit (MUST exceed 0.5% fees!)
    STOP_LOSS_PCT = 0.008          # 0.8% stop loss (tighter risk management)
    MAX_POSITION_PCT = 0.60        # Max 60% of capital per trade
    MAX_HOLD_MINUTES = 30          # 🕐 MAX 30 minutes - give trades TIME to develop!
    
    # 💀 FEE AWARENESS - Alpaca charges 0.25% per side (TAKER)
    ALPACA_FEE_PCT = 0.0025        # 0.25% per trade
    ROUND_TRIP_FEE_PCT = 0.005     # 0.50% round trip cost MINIMUM
    
    # Track when positions were opened
    position_open_times: Dict[str, float] = {}
    
    def __init__(self):
        logger.info("🦈🔪⚡ ORCA UNLEASHED - INITIALIZING ⚡🔪🦈")
        
        # Position timing
        self.position_open_times = {}
        
        # 🔮 PROBABILITY NEXUS - For smart kill validation!
        self.probability_nexus = None
        if PROBABILITY_NEXUS_AVAILABLE and AureonProbabilityNexus:
            try:
                self.probability_nexus = AureonProbabilityNexus()
                logger.info("🔮 Probability Nexus INITIALIZED - Batten Matrix validation ready!")
            except Exception as e:
                logger.warning(f"⚠️ Probability Nexus failed to init: {e}")
        
        # 🎯 HUNTING GROUNDS - Find best places to hunt!
        self.hunting_grounds = None
        if HUNTING_GROUNDS_AVAILABLE and OrcaHuntingGrounds:
            try:
                self.hunting_grounds = OrcaHuntingGrounds()
                logger.info("🎯 Hunting Grounds INITIALIZED - Smart venue selection ready!")
            except Exception as e:
                logger.warning(f"⚠️ Hunting Grounds failed to init: {e}")
        
        # Portfolio tracker
        self.portfolio_tracker = None
        if PORTFOLIO_TRACKER_AVAILABLE and get_real_portfolio_tracker:
            self.portfolio_tracker = get_real_portfolio_tracker()
            logger.info("💰👁️ Real Portfolio Tracker connected!")
        
        # Exchange clients
        self.alpaca = None
        self.kraken = None
        self.binance = None
        self._init_exchanges()
        
        # Hunting state
        self.active_hunts: List[OrcaHunt] = []
        self.completed_kills: List[OrcaKill] = []
        self.trades_this_hour = 0
        self.hour_start = time.time()
        
        # Session stats
        self.session_start = time.time()
        self.session_pnl = 0.0
        self.session_trades = 0
        self.session_wins = 0
        self.session_losses = 0
        
        # State persistence
        self.state_file = Path("orca_unleashed_state.json")
        self._load_state()
        
        logger.info("🦈 ORCA IS READY TO HUNT!")
        self._log_status()
    
    def _init_exchanges(self):
        """Initialize exchange connections."""
        exchange_count = 0
        
        if ALPACA_AVAILABLE:
            try:
                self.alpaca = AlpacaClient()
                exchange_count += 1
                logger.info("🦙 Alpaca CONNECTED")
            except Exception as e:
                logger.warning(f"🦙 Alpaca failed: {e}")
        
        if KRAKEN_AVAILABLE:
            try:
                self.kraken = get_kraken_client()
                exchange_count += 1
                logger.info("🐙 Kraken CONNECTED")
            except Exception as e:
                logger.warning(f"🐙 Kraken failed: {e}")
        
        if BINANCE_AVAILABLE:
            try:
                self.binance = get_binance_client()
                exchange_count += 1
                logger.info("🟡 Binance CONNECTED")
            except Exception as e:
                logger.warning(f"🟡 Binance failed: {e}")
        
        if exchange_count == 0:
            logger.error("🚨 NO EXCHANGES CONNECTED! Orca is BLIND!")
        else:
            logger.info(f"🌐 {exchange_count} exchanges connected")
    
    def _load_state(self):
        """Load previous state."""
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text())
                self.session_pnl = data.get('total_pnl', 0.0)
                self.session_trades = data.get('total_trades', 0)
                self.session_wins = data.get('total_wins', 0)
                self.session_losses = data.get('total_losses', 0)
                logger.info(f"📂 Loaded state: {self.session_trades} trades, ${self.session_pnl:.2f} P&L")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Save current state."""
        try:
            data = {
                'total_pnl': self.session_pnl,
                'total_trades': self.session_trades,
                'total_wins': self.session_wins,
                'total_losses': self.session_losses,
                'last_update': time.time()
            }
            tmp = self.state_file.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(self.state_file)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")
    
    def _log_status(self):
        """Log current status."""
        if self.portfolio_tracker:
            summary = self.portfolio_tracker.get_quick_summary()
            print()
            print("🦈═══════════════════════════════════════════════════🦈")
            print("         ORCA UNLEASHED - STATUS")
            print("🦈═══════════════════════════════════════════════════🦈")
            print(f"  💰 Available Capital: {summary['total_usd']}")
            print(f"  📊 Portfolio P&L: {summary['pnl']} ({summary['pnl_pct']})")
            print(f"  📈 Session P&L: ${self.session_pnl:.2f}")
            print(f"  🎯 Session Trades: {self.session_trades}")
            print(f"  ✅ Wins: {self.session_wins} | ❌ Losses: {self.session_losses}")
            if self.session_trades > 0:
                win_rate = (self.session_wins / self.session_trades) * 100
                print(f"  📊 Win Rate: {win_rate:.1f}%")
            print(f"  ⏰ Trades This Hour: {self.trades_this_hour}/{self.MAX_TRADES_PER_HOUR}")
            print("🦈═══════════════════════════════════════════════════🦈")
            print()
    
    def get_real_capital(self) -> float:
        """Get REAL AVAILABLE CASH (not positions)."""
        # For Alpaca, get actual available cash from account
        if self.alpaca:
            try:
                account = self.alpaca.get_account()
                cash = float(account.get('cash', 0) or 0)
                return cash
            except Exception:
                pass
        
        # Fallback to portfolio tracker
        if self.portfolio_tracker:
            snapshot = self.portfolio_tracker.get_real_portfolio()
            return snapshot.total_usd
        return 0.0
    
    def get_available_cash(self) -> float:
        """Get available cash specifically (not including positions)."""
        if self.alpaca:
            try:
                account = self.alpaca.get_account()
                # Use buying_power which accounts for existing orders
                buying_power = float(account.get('buying_power', 0) or 0)
                return buying_power
            except Exception:
                pass
        return self.get_real_capital()
    
    def validate_kill_decision(self, symbol: str, current_pnl_pct: float, hold_minutes: float) -> Tuple[bool, str, float]:
        """
        🔮 BATTEN MATRIX KILL VALIDATION 🔮
        
        Uses the Probability Nexus to make smart close decisions:
        - If probability says trend will CONTINUE in our favor → HOLD
        - If probability says trend will REVERSE → CLOSE NOW
        - If coherence is LOW → CLOSE (uncertain market)
        
        Returns: (should_close, reason, confidence)
        """
        # Default: use basic timer
        if not self.probability_nexus:
            if hold_minutes >= self.MAX_HOLD_MINUTES:
                return True, "⏰ Timer expired (no nexus)", 0.5
            return False, "Holding (no nexus)", 0.5
        
        try:
            # Get current market state and prediction
            state = self.probability_nexus.calculate_indicators()
            prediction = self.probability_nexus.predict(state)
            
            prob = prediction.probability
            confidence = prediction.confidence
            coherence = getattr(state, 'coherence', 0.5)
            direction = prediction.direction  # 'BULLISH' or 'BEARISH'
            
            # 🔮 VALIDATION PASS 1: Coherence Check
            # Low coherence = uncertain market = CLOSE
            if coherence < 0.5:
                return True, f"🔮 Low coherence ({coherence:.2f}) - market uncertain", coherence
            
            # 🔮 VALIDATION PASS 2: Trend Alignment
            # If we're LONG and nexus says BULLISH with high confidence → HOLD
            # If we're LONG and nexus says BEARISH → CLOSE
            we_are_long = True  # Our BTC position is always long for now
            trend_favorable = (we_are_long and direction == 'BULLISH') or \
                            (not we_are_long and direction == 'BEARISH')
            
            # 🔮 VALIDATION PASS 3: Confidence + Time Check
            # High confidence favorable trend → can hold longer
            # Low confidence or unfavorable → close sooner
            
            if trend_favorable and confidence >= 0.65:
                # Trend is in our favor with high confidence
                # Allow holding up to 2x normal time
                extended_time = self.MAX_HOLD_MINUTES * 1.5
                if hold_minutes >= extended_time:
                    return True, f"🔮 Extended hold expired ({hold_minutes:.1f}m)", confidence
                logger.info(f"🔮 Nexus says HOLD: {direction} @ {prob:.1%} conf={confidence:.2f} coh={coherence:.2f}")
                return False, f"🔮 Favorable: {direction} @ {confidence:.0%}", confidence
            
            elif not trend_favorable and confidence >= 0.55:
                # Trend is AGAINST us with medium+ confidence → CLOSE NOW
                return True, f"🔮 Trend reversal: {direction} @ {confidence:.0%}", confidence
            
            else:
                # Low confidence either way → use normal timer
                if hold_minutes >= self.MAX_HOLD_MINUTES:
                    return True, f"⏰ Timer expired (low conf {confidence:.0%})", confidence
                return False, f"Holding (low conf {confidence:.0%})", confidence
                
        except Exception as e:
            logger.warning(f"⚠️ Nexus validation error: {e}")
            # Fallback to timer
            if hold_minutes >= self.MAX_HOLD_MINUTES:
                return True, "⏰ Timer expired (nexus error)", 0.5
            return False, "Holding (nexus error)", 0.5
    
    def check_and_close_positions(self) -> List[OrcaKill]:
        """
        🔥 CHECK OPEN POSITIONS AND CLOSE IF TARGET/STOP HIT 🔥
        This is how we REALIZE gains and compound!
        
        🔥 FEE AWARENESS: Alpaca charges 0.25% per side (taker)
        Round trip = 0.50% MINIMUM cost before ANY profit!
        """
        kills = []
        
        if not self.alpaca:
            return kills
        
        try:
            positions = self.alpaca.get_positions()
            
            for pos in positions:
                symbol = pos.get('symbol', '')
                qty = float(pos.get('qty', 0) or 0)
                entry_price = float(pos.get('avg_entry_price', 0) or 0)
                current_price = float(pos.get('current_price', 0) or 0)
                unrealized_pnl = float(pos.get('unrealized_pl', 0) or 0)
                market_value = float(pos.get('market_value', 0) or 0)
                
                if qty == 0 or entry_price == 0 or current_price == 0:
                    continue
                
                # Calculate GROSS P&L percentage (before fees)
                gross_pnl_pct = (current_price - entry_price) / entry_price
                
                # Calculate FEE-ADJUSTED P&L (this is the REAL P&L!)
                # We already paid 0.25% to enter, will pay 0.25% to exit
                fee_adjusted_pnl_pct = gross_pnl_pct - self.ROUND_TRIP_FEE_PCT
                fee_adjusted_pnl_usd = unrealized_pnl - (market_value * self.ROUND_TRIP_FEE_PCT)
                
                logger.debug(f"📊 {symbol}: Gross={gross_pnl_pct:.2%} | After-Fee={fee_adjusted_pnl_pct:.2%}")
                
                # Check take profit (use GROSS because fees already factored into target)
                if gross_pnl_pct >= self.TAKE_PROFIT_PCT:
                    logger.info(f"🎯 TAKE PROFIT HIT! {symbol} @ {gross_pnl_pct:.2%} (net after fees: {fee_adjusted_pnl_pct:.2%})")
                    
                    # CLOSE THE POSITION - SELL!
                    try:
                        order = self.alpaca.place_order(
                            symbol=symbol,
                            qty=qty,
                            side='sell',
                            type='market',
                            time_in_force='gtc'
                        )
                        
                        if order:
                            # Calculate hold time
                            open_time = self.position_open_times.get(symbol, time.time())
                            hold_seconds = time.time() - open_time
                            
                            logger.info(f"💰 POSITION CLOSED: {symbol}")
                            logger.info(f"   Entry: ${entry_price:.2f}")
                            logger.info(f"   Exit: ${current_price:.2f}")
                            logger.info(f"   GROSS P&L: ${unrealized_pnl:.4f} ({gross_pnl_pct:.2%})")
                            logger.info(f"   💀 AFTER FEES: ${fee_adjusted_pnl_usd:.4f} ({fee_adjusted_pnl_pct:.2%})")
                            logger.info(f"   Hold time: {hold_seconds/60:.1f} minutes")
                            
                            kill = OrcaKill(
                                symbol=symbol,
                                exchange='alpaca',
                                direction='long',
                                entry_price=entry_price,
                                exit_price=current_price,
                                size_usd=market_value,
                                pnl_usd=fee_adjusted_pnl_usd,  # Use fee-adjusted P&L!
                                pnl_pct=fee_adjusted_pnl_pct * 100,
                                duration_seconds=hold_seconds,
                                timestamp=time.time()
                            )
                            kills.append(kill)
                            
                            # Count as real win only if AFTER-FEE profit
                            if fee_adjusted_pnl_usd > 0:
                                self.session_wins += 1
                            else:
                                self.session_losses += 1  # "Win" that lost money to fees!
                            self.session_pnl += fee_adjusted_pnl_usd
                            
                            # Clear timer
                            if symbol in self.position_open_times:
                                del self.position_open_times[symbol]
                            self._save_state()
                    except Exception as e:
                        logger.error(f"❌ Failed to close position: {e}")
                
                # Check stop loss (0.8%)
                elif gross_pnl_pct <= -self.STOP_LOSS_PCT:
                    logger.info(f"🛑 STOP LOSS HIT! {symbol} @ {gross_pnl_pct:.2%} (total loss with fees: {fee_adjusted_pnl_pct:.2%})")
                    
                    # CLOSE THE POSITION - SELL!
                    try:
                        order = self.alpaca.place_order(
                            symbol=symbol,
                            qty=qty,
                            side='sell',
                            type='market',
                            time_in_force='gtc'
                        )
                        
                        if order:
                            # Calculate hold time
                            open_time = self.position_open_times.get(symbol, time.time())
                            hold_seconds = time.time() - open_time
                            
                            logger.info(f"🔻 POSITION CLOSED (STOP): {symbol}")
                            logger.info(f"   Entry: ${entry_price:.2f}")
                            logger.info(f"   Exit: ${current_price:.2f}")
                            logger.info(f"   GROSS P&L: ${unrealized_pnl:.4f} ({gross_pnl_pct:.2%})")
                            logger.info(f"   💀 AFTER FEES: ${fee_adjusted_pnl_usd:.4f} ({fee_adjusted_pnl_pct:.2%})")
                            logger.info(f"   Hold time: {hold_seconds/60:.1f} minutes")
                            
                            kill = OrcaKill(
                                symbol=symbol,
                                exchange='alpaca',
                                direction='long',
                                entry_price=entry_price,
                                exit_price=current_price,
                                size_usd=market_value,
                                pnl_usd=fee_adjusted_pnl_usd,  # Use fee-adjusted P&L!
                                pnl_pct=fee_adjusted_pnl_pct * 100,
                                duration_seconds=hold_seconds,
                                timestamp=time.time()
                            )
                            kills.append(kill)
                            self.session_losses += 1
                            self.session_pnl += fee_adjusted_pnl_usd
                            
                            # Clear timer
                            if symbol in self.position_open_times:
                                del self.position_open_times[symbol]
                            self._save_state()
                    except Exception as e:
                        logger.error(f"❌ Failed to close position: {e}")
                
                else:
                    # Position still open - use PROBABILITY NEXUS for smart kill!
                    
                    # Track position open time if not already tracking
                    if symbol not in self.position_open_times:
                        self.position_open_times[symbol] = time.time()
                    
                    # Calculate how long position has been open
                    open_time = self.position_open_times.get(symbol, time.time())
                    hold_minutes = (time.time() - open_time) / 60
                    time_remaining = self.MAX_HOLD_MINUTES - hold_minutes
                    
                    # 🔮 USE PROBABILITY NEXUS TO VALIDATE KILL DECISION!
                    # Pass FEE-ADJUSTED P&L to nexus so it knows the REAL situation
                    should_close, close_reason, nexus_confidence = self.validate_kill_decision(
                        symbol, fee_adjusted_pnl_pct, hold_minutes
                    )
                    
                    if should_close:
                        logger.info(f"🔮🔪 NEXUS KILL: {symbol} - {close_reason}")
                        logger.info(f"   Hold: {hold_minutes:.1f}m | Gross: {gross_pnl_pct:+.2%} | Net: {fee_adjusted_pnl_pct:+.2%}")
                        
                        try:
                            order = self.alpaca.place_order(
                                symbol=symbol,
                                qty=qty,
                                side='sell',
                                type='market',
                                time_in_force='gtc'
                            )
                            
                            if order:
                                logger.info(f"🔮 POSITION CLOSED (NEXUS): {symbol}")
                                logger.info(f"   Entry: ${entry_price:.2f}")
                                logger.info(f"   Exit: ${current_price:.2f}")
                                logger.info(f"   GROSS P&L: ${unrealized_pnl:.4f} ({gross_pnl_pct:.2%})")
                                logger.info(f"   💀 AFTER FEES: ${fee_adjusted_pnl_usd:.4f} ({fee_adjusted_pnl_pct:.2%})")
                                logger.info(f"   Reason: {close_reason}")
                                
                                kill = OrcaKill(
                                    symbol=symbol,
                                    exchange='alpaca',
                                    direction='long',
                                    entry_price=entry_price,
                                    exit_price=current_price,
                                    size_usd=market_value,
                                    pnl_usd=fee_adjusted_pnl_usd,  # Use fee-adjusted!
                                    pnl_pct=fee_adjusted_pnl_pct * 100,
                                    duration_seconds=hold_minutes * 60,
                                    timestamp=time.time()
                                )
                                kills.append(kill)
                                
                                # Count as real win only if AFTER-FEE profit
                                if fee_adjusted_pnl_usd > 0:
                                    self.session_wins += 1
                                else:
                                    self.session_losses += 1
                                    
                                self.session_pnl += fee_adjusted_pnl_usd
                                
                                # Clear the timer
                                del self.position_open_times[symbol]
                                self._save_state()
                        except Exception as e:
                            logger.error(f"❌ Failed to close position (nexus): {e}")
                    else:
                        # Show status with fee-adjusted info
                        logger.info(f"📊 {symbol}: Gross={gross_pnl_pct:+.2%} Net={fee_adjusted_pnl_pct:+.2%} | 🔮 {close_reason} | ⏰ {time_remaining:.1f}m")
        
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
        
        return kills
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed."""
        # Check hourly limit
        if time.time() - self.hour_start > 3600:
            self.trades_this_hour = 0
            self.hour_start = time.time()
        
        if self.trades_this_hour >= self.MAX_TRADES_PER_HOUR:
            return False, f"⏰ Hourly limit reached ({self.MAX_TRADES_PER_HOUR} trades)"
        
        # Check capital - use AVAILABLE CASH not total equity
        capital = self.get_available_cash()
        if capital < self.MIN_TRADE_SIZE_USD:
            return False, f"💸 Insufficient capital: ${capital:.2f} < ${self.MIN_TRADE_SIZE_USD}"
        
        return True, "✅ Ready to hunt!"
    
    def calculate_position_size(self) -> float:
        """Calculate safe position size based on AVAILABLE CASH."""
        # Use available cash, not total equity (includes positions)
        available = self.get_available_cash()
        
        # Leave 10% buffer for slippage/fees
        safe_capital = available * 0.90
        
        # Never risk more than MAX_POSITION_PCT
        max_size = safe_capital * self.MAX_POSITION_PCT
        
        # But at least MIN_TRADE_SIZE if we can afford it
        if safe_capital >= self.MIN_TRADE_SIZE_USD:
            size = max(self.MIN_TRADE_SIZE_USD, min(max_size, safe_capital * 0.5))
        else:
            # Use what we have minus buffer
            size = max(1.0, safe_capital)
        
        return size
    
    def scan_alpaca_opportunities(self) -> List[OrcaHunt]:
        """Scan Alpaca for hunting opportunities."""
        opportunities = []
        
        if not self.alpaca:
            return opportunities
        
        try:
            # Crypto pairs on Alpaca
            symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'AVAX/USD', 'LINK/USD']
            
            for symbol in symbols:
                try:
                    ticker = self.alpaca.get_ticker(symbol)
                    if not ticker:
                        continue
                    
                    bid = float(ticker.get('bid', 0) or 0)
                    ask = float(ticker.get('ask', 0) or 0)
                    # Alpaca uses 'price' not 'last'
                    last = float(ticker.get('price', 0) or ticker.get('last', 0) or 0)
                    
                    if not (bid > 0 and ask > 0):
                        continue
                    
                    # Use mid price if last is missing
                    if last == 0:
                        last = (bid + ask) / 2
                    
                    mid_price = (bid + ask) / 2
                    spread_pct = ((ask - bid) / mid_price) * 100 if mid_price else 0
                    
                    # Calculate confidence based on multiple factors
                    confidence = 0.55  # Base confidence (slightly higher)
                    direction = 'long'  # Default to long (most reliable)
                    reasoning = []
                    
                    # Factor 1: Spread quality (more lenient thresholds)
                    if spread_pct < 0.15:
                        confidence += 0.20
                        reasoning.append(f"🔥 Tight spread: {spread_pct:.3f}%")
                    elif spread_pct < 0.25:
                        confidence += 0.10
                        reasoning.append(f"✅ Good spread: {spread_pct:.3f}%")
                    elif spread_pct < 0.40:
                        confidence += 0.05
                        reasoning.append(f"📊 Acceptable spread: {spread_pct:.3f}%")
                    else:
                        confidence -= 0.10
                        reasoning.append(f"⚠️ Wide spread: {spread_pct:.3f}%")
                    
                    # Factor 2: Price position relative to bid/ask
                    # If last is near ask, buyers are aggressive (bullish)
                    # If last is near bid, sellers are aggressive (bearish)
                    if ask > bid:
                        position_in_spread = (last - bid) / (ask - bid)
                        if position_in_spread > 0.7:
                            confidence += 0.15
                            reasoning.append("📈 Buyers aggressive (last near ask)")
                            direction = 'long'
                        elif position_in_spread < 0.3:
                            confidence += 0.10
                            reasoning.append("📉 Sellers aggressive (last near bid)")
                            direction = 'short'  # Could short but riskier
                    
                    # Factor 3: Check if price is reasonable (sanity check)
                    if symbol == 'BTC/USD' and (last < 50000 or last > 200000):
                        confidence -= 0.20
                        reasoning.append("⚠️ BTC price seems off")
                    elif symbol == 'ETH/USD' and (last < 1500 or last > 10000):
                        confidence -= 0.20
                        reasoning.append("⚠️ ETH price seems off")
                    
                    # Only long for now (safer with limited capital)
                    direction = 'long'
                    
                    # Log what we found
                    logger.debug(f"   {symbol}: spread={spread_pct:.3f}%, conf={confidence:.2f}, {reasoning}")
                    
                    if confidence >= self.MIN_CONFIDENCE:
                        size = self.calculate_position_size()
                        entry = ask  # Buy at ask for market order
                        target = entry * (1 + self.TAKE_PROFIT_PCT)
                        stop = entry * (1 - self.STOP_LOSS_PCT)
                        
                        hunt = OrcaHunt(
                            symbol=symbol,
                            exchange='alpaca',
                            direction=direction,
                            confidence=confidence,
                            entry_price=entry,
                            target_price=target,
                            stop_price=stop,
                            size_usd=size,
                            reasoning=reasoning
                        )
                        opportunities.append(hunt)
                        logger.info(f"🎯 Found opportunity: {symbol} @ {confidence:.1%}")
                
                except Exception as e:
                    logger.debug(f"Error scanning {symbol}: {e}")
        
        except Exception as e:
            logger.warning(f"Alpaca scan error: {e}")
        
        return opportunities

    def scan_binance_opportunities(self) -> List[OrcaHunt]:
        """Scan Binance for hunting opportunities."""
        opportunities = []
        if not self.binance:
            return opportunities
            
        try:
            # High volume pairs on Binance
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT']
            
            for symbol in symbols:
                try:
                    ticker = self.binance.get_24h_ticker(symbol)
                    if not ticker:
                        continue
                        
                    bid = float(ticker.get('bid', 0))
                    ask = float(ticker.get('ask', 0))
                    last = float(ticker.get('price', 0))
                    
                    if not (bid > 0 and ask > 0):
                        continue
                        
                    mid_price = (bid + ask) / 2
                    spread_pct = ((ask - bid) / mid_price) * 100 if mid_price else 0
                    
                    # Logic copied from Alpaca scan
                    confidence = 0.55
                    direction = 'long'
                    reasoning = []
                    
                    if spread_pct < 0.10: # Binance usually tighter
                        confidence += 0.20
                        reasoning.append(f"🔥 Tight spread: {spread_pct:.3f}%")
                    elif spread_pct < 0.20:
                        confidence += 0.10
                        reasoning.append(f"✅ Good spread: {spread_pct:.3f}%")
                    elif spread_pct < 0.30:
                        confidence += 0.05
                        reasoning.append(f"📊 Acceptable spread: {spread_pct:.3f}%")
                    else:
                        confidence -= 0.10
                        reasoning.append(f"⚠️ Wide spread: {spread_pct:.3f}%")
                        
                    if ask > bid:
                        position_in_spread = (last - bid) / (ask - bid)
                        if position_in_spread > 0.7:
                            confidence += 0.15
                            reasoning.append("📈 Buyers aggressive")
                            direction = 'long'
                        elif position_in_spread < 0.3:
                            confidence += 0.10
                            reasoning.append("📉 Sellers aggressive")
                            direction = 'short'
                            
                    if confidence >= self.MIN_CONFIDENCE:
                        size = self.calculate_position_size()
                        entry = ask
                        target = entry * (1 + self.TAKE_PROFIT_PCT)
                        stop = entry * (1 - self.STOP_LOSS_PCT)
                        
                        hunt = OrcaHunt(
                            symbol=symbol,
                            exchange='binance',
                            direction=direction,
                            confidence=confidence,
                            entry_price=entry,
                            target_price=target,
                            stop_price=stop,
                            size_usd=size,
                            reasoning=reasoning
                        )
                        opportunities.append(hunt)
                        logger.info(f"🎯 Found Binance opportunity: {symbol} @ {confidence:.1%}")
                except Exception as e:
                    logger.debug(f"Error scanning Binance {symbol}: {e}")
        except Exception as e:
            logger.warning(f"Binance scan error: {e}")
            
        return opportunities

    def scan_kraken_opportunities(self) -> List[OrcaHunt]:
        """Scan Kraken for hunting opportunities."""
        opportunities = []
        if not self.kraken:
            return opportunities
            
        try:
            # Kraken symbols
            symbols = ['XBTUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'ADAUSD']
            
            for symbol in symbols:
                try:
                    ticker = self.kraken.get_ticker(symbol)
                    if not ticker:
                        continue
                    
                    # Kraken client normalizes to {symbol, price, bid, ask} with floats
                    bid = ticker.get('bid', 0.0)
                    ask = ticker.get('ask', 0.0)
                    last = ticker.get('price', 0.0)
                    
                    if not (bid > 0 and ask > 0):
                        continue
                        
                    mid_price = (bid + ask) / 2
                    spread_pct = ((ask - bid) / mid_price) * 100 if mid_price else 0
                    
                    confidence = 0.55
                    direction = 'long'
                    reasoning = []
                    
                    if spread_pct < 0.15:
                        confidence += 0.20
                        reasoning.append(f"🔥 Tight spread: {spread_pct:.3f}%")
                    elif spread_pct < 0.25:
                        confidence += 0.10
                        reasoning.append(f"✅ Good spread: {spread_pct:.3f}%")
                    else:
                        confidence -= 0.05
                        reasoning.append(f"📊 Spread: {spread_pct:.3f}%")
                        
                    if ask > bid:
                        position_in_spread = (last - bid) / (ask - bid)
                        if position_in_spread > 0.7:
                            confidence += 0.15
                            reasoning.append("📈 Buyers aggressive")
                        elif position_in_spread < 0.3:
                            confidence += 0.10
                            reasoning.append("📉 Sellers aggressive")
                            direction = 'short'
                            
                    if confidence >= self.MIN_CONFIDENCE:
                        size = self.calculate_position_size()
                        entry = ask
                        target = entry * (1 + self.TAKE_PROFIT_PCT)
                        stop = entry * (1 - self.STOP_LOSS_PCT)
                        
                        hunt = OrcaHunt(
                            symbol=symbol,
                            exchange='kraken',
                            direction=direction,
                            confidence=confidence,
                            entry_price=entry,
                            target_price=target,
                            stop_price=stop,
                            size_usd=size,
                            reasoning=reasoning
                        )
                        opportunities.append(hunt)
                        logger.info(f"🎯 Found Kraken opportunity: {symbol} @ {confidence:.1%}")
                except Exception as e:
                    logger.debug(f"Error scanning Kraken {symbol}: {e}")
        except Exception as e:
            logger.warning(f"Kraken scan error: {e}")
            
        return opportunities
    
    def scan_all_markets(self) -> List[OrcaHunt]:
        """Scan all markets for opportunities."""
        all_opportunities = []
        
        # Scan each exchange
        all_opportunities.extend(self.scan_alpaca_opportunities())
        all_opportunities.extend(self.scan_binance_opportunities())
        all_opportunities.extend(self.scan_kraken_opportunities())
        
        # Sort by confidence
        all_opportunities.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_opportunities
    
    def execute_hunt(self, hunt: OrcaHunt, dry_run: bool = True) -> Optional[OrcaKill]:
        """
        Execute a hunt (trade).
        
        Args:
            hunt: The hunting opportunity
            dry_run: If True, simulate only (no real trade)
        """
        can_trade, reason = self.can_trade()
        if not can_trade:
            logger.warning(f"🚫 Cannot trade: {reason}")
            return None
        
        logger.info(f"🦈🔪 EXECUTING HUNT: {hunt.symbol} @ {hunt.exchange}")
        logger.info(f"   Direction: {hunt.direction.upper()}")
        logger.info(f"   Confidence: {hunt.confidence:.1%}")
        logger.info(f"   Size: ${hunt.size_usd:.2f}")
        logger.info(f"   Entry: ${hunt.entry_price:.4f}")
        logger.info(f"   Target: ${hunt.target_price:.4f}")
        logger.info(f"   Stop: ${hunt.stop_price:.4f}")
        
        if dry_run:
            logger.info("   🧪 DRY RUN - No real trade executed")
            # Simulate a small win for testing
            simulated_pnl = hunt.size_usd * 0.005  # 0.5% simulated gain
            self.session_pnl += simulated_pnl
            self.session_trades += 1
            self.session_wins += 1
            self.trades_this_hour += 1
            self._save_state()
            
            return OrcaKill(
                symbol=hunt.symbol,
                exchange=hunt.exchange,
                direction=hunt.direction,
                entry_price=hunt.entry_price,
                exit_price=hunt.target_price,
                size_usd=hunt.size_usd,
                pnl_usd=simulated_pnl,
                pnl_pct=0.5,
                duration_seconds=60,
                timestamp=time.time()
            )
        
        # REAL TRADE EXECUTION
        try:
            if hunt.exchange == 'alpaca' and self.alpaca:
                # Calculate quantity
                qty = hunt.size_usd / hunt.entry_price
                
                # Place order using place_order (not submit_order!)
                side = 'buy' if hunt.direction == 'long' else 'sell'
                order = self.alpaca.place_order(
                    symbol=hunt.symbol.replace('/', ''),
                    qty=qty,
                    side=side,
                    type='market',
                    time_in_force='gtc'
                )
                
                if order:
                    logger.info(f"✅ Order placed: {order.get('id')}")
                    self.trades_this_hour += 1
                    self.session_trades += 1
                    self._save_state()
                    # Would need to track and close position...
                else:
                    logger.error("❌ Order failed!")
                    return None

            elif hunt.exchange == 'binance' and self.binance:
                qty = hunt.size_usd / hunt.entry_price
                side = 'buy' if hunt.direction == 'long' else 'sell'
                
                order = self.binance.place_market_order(
                    symbol=hunt.symbol,
                    side=side,
                    quantity=qty
                )
                
                if order and not order.get('rejected'):
                    logger.info(f"✅ Binance Order placed: {order}")
                    self.trades_this_hour += 1
                    self.session_trades += 1
                    self._save_state()
                else:
                    logger.error(f"❌ Binance Order failed: {order}")
                    return None

            elif hunt.exchange == 'kraken' and self.kraken:
                qty = hunt.size_usd / hunt.entry_price
                side = 'buy' if hunt.direction == 'long' else 'sell'
                
                order = self.kraken.place_market_order(
                    symbol=hunt.symbol,
                    side=side,
                    quantity=qty
                )
                
                if order:
                    logger.info(f"✅ Kraken Order placed: {order}")
                    self.trades_this_hour += 1
                    self.session_trades += 1
                    self._save_state()
                else:
                    logger.error("❌ Kraken Order failed!")
                    return None
        
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            return None
        
        return None
    
    def hunt_cycle(self, dry_run: bool = True) -> None:
        """Run one hunting cycle."""
        logger.info("🦈 Starting hunt cycle...")
        
        # 🔥 FIRST: Check existing positions and close if target/stop hit!
        if not dry_run:
            kills = self.check_and_close_positions()
            for kill in kills:
                self.completed_kills.append(kill)
                logger.info(f"💰 REALIZED GAIN: ${kill.pnl_usd:+.4f} ({kill.pnl_pct:+.2f}%)")
        
        # Check if we can trade
        can_trade, reason = self.can_trade()
        if not can_trade:
            logger.info(f"⏸️ {reason}")
            return
        
        # Scan for opportunities
        opportunities = self.scan_all_markets()
        
        if not opportunities:
            logger.info("🔍 No opportunities found (waiting for the perfect moment...)")
            return
        
        # Take the best opportunity above threshold
        best = opportunities[0]
        
        if best.confidence < self.MIN_CONFIDENCE:
            logger.info(f"🔍 Best opportunity ({best.confidence:.1%}) below threshold ({self.MIN_CONFIDENCE:.1%})")
            return
        
        logger.info(f"🎯 Found opportunity: {best.symbol} @ {best.confidence:.1%} confidence")
        
        # Execute!
        kill = self.execute_hunt(best, dry_run=dry_run)
        
        if kill:
            self.completed_kills.append(kill)
            logger.info(f"💰 KILL COMPLETE: ${kill.pnl_usd:+.2f} ({kill.pnl_pct:+.2f}%)")
    
    def run(self, duration_minutes: int = 60, dry_run: bool = True, cycle_seconds: int = 30):
        """
        Run the Orca hunting session.
        
        Args:
            duration_minutes: How long to run
            dry_run: If True, simulate trades
            cycle_seconds: Seconds between hunt cycles
        """
        print()
        print("🦈" * 30)
        print()
        print("    ⚡🔪 ORCA UNLEASHED - HUNTING SESSION 🔪⚡")
        print()
        print("🦈" * 30)
        print()
        
        if dry_run:
            print("    🧪 DRY RUN MODE - No real trades!")
        else:
            print("    🚨 LIVE MODE - Real money on the line!")
        
        print()
        self._log_status()
        
        end_time = time.time() + (duration_minutes * 60)
        cycles = 0
        
        try:
            while time.time() < end_time:
                cycles += 1
                logger.info(f"━━━ Cycle {cycles} ━━━")
                
                self.hunt_cycle(dry_run=dry_run)
                
                # Status every 5 cycles
                if cycles % 5 == 0:
                    self._log_status()
                
                # Wait for next cycle
                remaining = end_time - time.time()
                if remaining > cycle_seconds:
                    time.sleep(cycle_seconds)
                elif remaining > 0:
                    time.sleep(remaining)
        
        except KeyboardInterrupt:
            print("\n🛑 Hunt interrupted by user")
        
        # Final status
        print()
        print("🦈" * 30)
        print()
        print("    SESSION COMPLETE!")
        print()
        self._log_status()
        print("🦈" * 30)


def main():
    """Run the unleashed Orca!"""
    import argparse
    
    parser = argparse.ArgumentParser(description="🦈 ORCA UNLEASHED - The Killer Whale Hunts!")
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode (real trades!)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    parser.add_argument("--cycle", type=int, default=30, help="Seconds between cycles")
    parser.add_argument("--status", action="store_true", help="Just show status")
    parser.add_argument("--force", action="store_true", help="Skip confirmation (DANGEROUS!)")
    args = parser.parse_args()
    
    orca = OrcaUnleashed()
    
    if args.status:
        orca._log_status()
        return
    
    dry_run = not args.live
    
    if not dry_run and not args.force:
        print()
        print("🚨" * 20)
        print()
        print("    ⚠️  WARNING: LIVE TRADING MODE! ⚠️")
        print("    Real money will be used!")
        print()
        print("🚨" * 20)
        print()
        response = input("Type 'HUNT' to confirm: ")
        if response != 'HUNT':
            print("Aborted.")
            return
    
    if not dry_run:
        logger.info("🔴🔴🔴 LIVE MODE ACTIVATED - REAL MONEY! 🔴🔴🔴")
    
    orca.run(
        duration_minutes=args.duration,
        dry_run=dry_run,
        cycle_seconds=args.cycle
    )


if __name__ == "__main__":
    main()
