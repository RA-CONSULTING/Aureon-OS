#!/usr/bin/env python3
"""
🐋 ORCA DUAL HUNTER - Hunts on BOTH Alpaca & Kraken 🐋
=====================================================
Total Capital: $24.46 ($9.33 Alpaca + $15.13 Kraken)

Fee-Aware Settings:
- Alpaca: 0.25%/side = 0.50% round trip
- Kraken: 0.26%/side = 0.52% round trip
- Take Profit: 1.5% (nets ~1.0% after fees)
- Stop Loss: 0.8%
- Max Hold: 30 minutes

Best Hunting Grounds (by hunt score):
- DOGE: 2.9 (5% volatility)
- SOL: 2.7 (4.5% volatility)
- ETH: 2.2 (3% volatility)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import time
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from decimal import Decimal, ROUND_DOWN

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FEE-AWARE CONFIGURATION
# ============================================================================
# After discovering fees were HIDDEN and eating all profit:
# - Alpaca fees: 0.25% per side = 0.50% round trip
# - Kraken fees: 0.26% per side = 0.52% round trip
# - Old TP of 0.5% = break even = NO PROFIT
# - New TP of 1.5% = 1.0% net profit after fees

TAKE_PROFIT_PCT = 0.015      # 1.5% gross = ~1.0% net after fees
STOP_LOSS_PCT = 0.008        # 0.8% - tight but reasonable
MAX_HOLD_MINUTES = 30        # Give trades time to develop
POSITION_SIZE_PCT = 0.90     # Use 90% of available capital per trade

# Fee rates (discovered the hard way!)
ALPACA_FEE_PCT = 0.0025      # 0.25% per side
# Kraken fee is now dynamic — looked up from KrakenFeeTracker at runtime.
# At ~$123K 30d volume: Tier 4 taker = 0.22%. Fallback used when tracker unavailable.
KRAKEN_FEE_PCT = 0.0022      # 0.22% per side (Tier 4 default, updated dynamically)

# Import dynamic Kraken fee tracker (optional — falls back to KRAKEN_FEE_PCT)
try:
    from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker as _get_kft
    _KRAKEN_FEE_TRACKER_AVAILABLE = True
except ImportError:
    _get_kft = None
    _KRAKEN_FEE_TRACKER_AVAILABLE = False

# Best hunting grounds (from our analysis)
ALPACA_HUNT_SYMBOLS = ['DOGE/USD', 'SOL/USD', 'ETH/USD', 'AVAX/USD', 'BTC/USD']
KRAKEN_HUNT_SYMBOLS = ['DOGEUSD', 'SOLUSD', 'ETHUSD', 'AVAXUSD', 'XBTUSD']  # Kraken format

# Minimum movement to consider (after analyzing volatility)
MIN_MOVE_PCT = 0.008  # 0.8% minimum daily move

STATE_FILE = "orca_dual_hunter_state.json"


@dataclass
class Position:
    """Unified position tracking across exchanges."""
    exchange: str           # 'alpaca' or 'kraken'
    symbol: str
    side: str               # 'long'
    qty: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    fee_rate: float = 0.0025  # Per-side fee rate
    
    @property
    def round_trip_fee_pct(self) -> float:
        return self.fee_rate * 2
    
    @property
    def net_pnl_pct(self) -> float:
        """P&L after accounting for round-trip fees."""
        return self.unrealized_pnl_pct - self.round_trip_fee_pct
    
    @property
    def net_pnl_usd(self) -> float:
        """Dollar P&L after fees."""
        position_value = self.qty * self.entry_price
        fee_cost = position_value * self.round_trip_fee_pct
        return self.unrealized_pnl - fee_cost
    
    @property
    def hold_minutes(self) -> float:
        return (datetime.now() - self.entry_time).total_seconds() / 60


@dataclass
class ExchangeStatus:
    """Status for one exchange."""
    name: str
    connected: bool = False
    cash: float = 0.0
    equity: float = 0.0
    position: Optional[Position] = None
    last_error: str = ""
    trades_today: int = 0
    wins_today: int = 0
    pnl_today: float = 0.0


class OrcaDualHunter:
    """
    🐋 THE DUAL PLATFORM ORCA 🐋
    
    Hunts across BOTH Alpaca and Kraken simultaneously.
    Fee-aware trading with proper profit targets.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.running = False
        
        # Exchange clients
        self.alpaca = None
        self.kraken = None
        
        # Status for each exchange
        self.alpaca_status = ExchangeStatus(name='Alpaca')
        self.kraken_status = ExchangeStatus(name='Kraken')
        
        # Global stats
        self.total_trades = 0
        self.total_wins = 0
        self.total_pnl = 0.0
        
        self._init_exchanges()
        self._load_state()
    
    def _init_exchanges(self):
        """Initialize both exchange clients."""
        # Load .env file if present (robust path search)
        try:
            from dotenv import load_dotenv
            from pathlib import Path

            dotenv_candidates = []
            explicit = os.getenv("DOTENV_PATH")
            if explicit:
                dotenv_candidates.append(Path(explicit))

            dotenv_candidates.append(Path.cwd() / ".env")
            dotenv_candidates.append(Path(__file__).resolve().parent / ".env")

            loaded = False
            for candidate in dotenv_candidates:
                try:
                    if candidate.exists():
                        load_dotenv(dotenv_path=str(candidate), override=False)
                        loaded = True
                        break
                except Exception:
                    continue

            if not loaded:
                load_dotenv(override=False)
        except ImportError:
            pass
        
        # Alpaca
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.live import CryptoDataStream
            
            api_key = os.environ.get('ALPACA_API_KEY') or os.environ.get('APCA_API_KEY_ID')
            api_secret = (
                os.environ.get('ALPACA_SECRET_KEY')
                or os.environ.get('ALPACA_API_SECRET')
                or os.environ.get('ALPACA_SECRET')
                or os.environ.get('APCA_API_SECRET_KEY')
            )
            
            if api_key and api_secret:
                # Check if paper trading is configured
                # Stage AD: ALPACA_PAPER default flipped to 'false' to align with the
                # rest of the codebase (alpaca_client.py and others). Live by default.
                paper_mode = os.environ.get('ALPACA_PAPER', 'false').lower() in ('true', '1', 'yes')
                self.alpaca = TradingClient(api_key, api_secret, paper=paper_mode)
                self.alpaca_status.connected = True
                logger.info(f"✅ Alpaca connected ({'PAPER' if paper_mode else 'LIVE'})")
            else:
                logger.warning("⚠️ Alpaca API keys not found")
        except Exception as e:
            logger.warning(f"⚠️ Alpaca connection failed: {e}")
            self.alpaca_status.last_error = str(e)
        
        # Kraken (using our adapter — already wires KrakenFeeTracker internally)
        try:
            from aureon.exchanges.kraken_trading_adapter import KrakenTradingAdapter
            self.kraken = KrakenTradingAdapter()
            self.kraken_status.connected = True
            # Refresh the module-level fallback with the live tier rate
            global KRAKEN_FEE_PCT
            KRAKEN_FEE_PCT = self.kraken.get_fee_rate(is_taker=True)
            logger.info(f"✅ Kraken connected  (taker fee={KRAKEN_FEE_PCT*100:.3f}%)")
        except Exception as e:
            logger.warning(f"⚠️ Kraken connection failed: {e}")
            self.kraken_status.last_error = str(e)
    
    def _load_state(self):
        """Load persisted state."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.total_trades = state.get('total_trades', 0)
                    self.total_wins = state.get('total_wins', 0)
                    self.total_pnl = state.get('total_pnl', 0.0)
                    logger.info(f"📂 Loaded state: {self.total_trades} trades, ${self.total_pnl:.4f} P&L")
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Persist state to disk."""
        state = {
            'total_trades': self.total_trades,
            'total_wins': self.total_wins,
            'total_pnl': self.total_pnl,
            'last_update': datetime.now().isoformat()
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")
    
    def update_alpaca_status(self):
        """Update Alpaca account and position status."""
        if not self.alpaca:
            return
        
        try:
            # Get account
            account = self.alpaca.get_account()
            self.alpaca_status.cash = float(account.cash)
            self.alpaca_status.equity = float(account.equity)
            
            # Get positions
            positions = self.alpaca.get_all_positions()
            if positions:
                pos = positions[0]  # We only hold one at a time
                symbol = pos.symbol.replace('USD', '/USD')
                
                self.alpaca_status.position = Position(
                    exchange='alpaca',
                    symbol=symbol,
                    side='long',
                    qty=float(pos.qty),
                    entry_price=float(pos.avg_entry_price),
                    entry_time=datetime.now(),  # We'd need to track this properly
                    current_price=float(pos.current_price),
                    unrealized_pnl=float(pos.unrealized_pl),
                    unrealized_pnl_pct=float(pos.unrealized_plpc),
                    fee_rate=ALPACA_FEE_PCT
                )
            else:
                self.alpaca_status.position = None
                
        except Exception as e:
            logger.error(f"❌ Alpaca status update failed: {e}")
            self.alpaca_status.last_error = str(e)
    
    def update_kraken_status(self):
        """Update Kraken account and position status."""
        if not self.kraken:
            return
        
        try:
            # Get account
            account = self.kraken.get_account()
            self.kraken_status.cash = float(account.get('cash', 0.0))
            self.kraken_status.equity = float(account.get('equity', 0.0))
            
            # Get positions (returns a LIST from our adapter)
            positions = self.kraken.get_positions()
            
            # Find our largest position
            largest_pos = None
            largest_value = 0
            
            for pos_data in positions:  # It's a list, not dict
                value = pos_data['qty'] * pos_data['current_price']
                if value > largest_value and value > 1.0:  # At least $1
                    largest_value = value
                    largest_pos = pos_data
            
            if largest_pos:
                self.kraken_status.position = Position(
                    exchange='kraken',
                    symbol=largest_pos['symbol'],
                    side='long',
                    qty=largest_pos['qty'],
                    entry_price=largest_pos['avg_entry_price'],
                    entry_time=datetime.now(),
                    current_price=largest_pos['current_price'],
                    unrealized_pnl=largest_pos['unrealized_pl'],
                    unrealized_pnl_pct=largest_pos['unrealized_plpc'],
                    fee_rate=KRAKEN_FEE_PCT
                )
            else:
                self.kraken_status.position = None
                
        except Exception as e:
            logger.error(f"❌ Kraken status update failed: {e}")
            self.kraken_status.last_error = str(e)
    
    def get_best_opportunity(self, exchange: str) -> Optional[Dict]:
        """Find the best trading opportunity on an exchange."""
        if exchange == 'alpaca':
            return self._scan_alpaca()
        elif exchange == 'kraken':
            return self._scan_kraken()
        return None
    
    def _scan_alpaca(self) -> Optional[Dict]:
        """Scan Alpaca for opportunities."""
        if not self.alpaca:
            return None
        
        try:
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoLatestQuoteRequest
            
            data_client = CryptoHistoricalDataClient()
            
            best_opp = None
            best_score = 0
            
            for symbol in ALPACA_HUNT_SYMBOLS:
                try:
                    # Get quote
                    req = CryptoLatestQuoteRequest(symbol_or_symbols=[symbol])
                    quotes = data_client.get_crypto_latest_quote(req)
                    
                    if symbol in quotes:
                        quote = quotes[symbol]
                        bid = float(quote.bid_price)
                        ask = float(quote.ask_price)
                        spread_pct = (ask - bid) / bid if bid > 0 else 1
                        
                        # Simple momentum check - we'd want candles for proper analysis
                        # For now, prefer tighter spreads as indicator of liquidity
                        score = (1 / (spread_pct + 0.001))  # Higher score for tighter spread
                        
                        if score > best_score:
                            best_score = score
                            best_opp = {
                                'symbol': symbol,
                                'price': ask,
                                'spread_pct': spread_pct,
                                'score': score,
                                'exchange': 'alpaca'
                            }
                except Exception as e:
                    continue
            
            return best_opp
            
        except Exception as e:
            logger.error(f"Alpaca scan failed: {e}")
            return None
    
    def _scan_kraken(self) -> Optional[Dict]:
        """Scan Kraken for opportunities."""
        if not self.kraken:
            return None
        
        try:
            best_opp = None
            best_score = 0
            
            for symbol in KRAKEN_HUNT_SYMBOLS:
                try:
                    ticker = self.kraken.get_ticker(symbol)
                    if ticker:
                        bid = ticker.get('bid', 0)
                        ask = ticker.get('ask', 0)
                        last = ticker.get('last', 0)
                        
                        if bid > 0 and ask > 0:
                            spread_pct = (ask - bid) / bid
                            score = (1 / (spread_pct + 0.001))
                            
                            if score > best_score:
                                best_score = score
                                best_opp = {
                                    'symbol': symbol,
                                    'price': ask,
                                    'spread_pct': spread_pct,
                                    'score': score,
                                    'exchange': 'kraken'
                                }
                except Exception as e:
                    continue
            
            return best_opp
            
        except Exception as e:
            logger.error(f"Kraken scan failed: {e}")
            return None
    
    def enter_position(self, exchange: str, symbol: str, price: float) -> bool:
        """Enter a position on the specified exchange."""
        if exchange == 'alpaca':
            return self._enter_alpaca(symbol, price)
        elif exchange == 'kraken':
            return self._enter_kraken(symbol, price)
        return False
    
    def _enter_alpaca(self, symbol: str, price: float) -> bool:
        """Enter position on Alpaca."""
        if not self.alpaca:
            return False
        
        try:
            cash = self.alpaca_status.cash
            position_value = cash * POSITION_SIZE_PCT
            qty = position_value / price
            
            # Alpaca requires proper formatting
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            # Format symbol for Alpaca
            alpaca_symbol = symbol.replace('/', '')
            
            if self.dry_run:
                logger.info(f"🔶 [DRY RUN] Would BUY {qty:.6f} {alpaca_symbol} @ ${price:.4f}")
                # Simulate the position
                self.alpaca_status.position = Position(
                    exchange='alpaca',
                    symbol=symbol,
                    side='long',
                    qty=qty,
                    entry_price=price,
                    entry_time=datetime.now(),
                    current_price=price,
                    fee_rate=ALPACA_FEE_PCT
                )
                return True
            
            # Real order
            order = MarketOrderRequest(
                symbol=alpaca_symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            result = self.alpaca.submit_order(order)
            logger.info(f"🟢 BOUGHT {qty:.6f} {alpaca_symbol} @ ${price:.4f}")
            
            self.alpaca_status.position = Position(
                exchange='alpaca',
                symbol=symbol,
                side='long',
                qty=qty,
                entry_price=price,
                entry_time=datetime.now(),
                current_price=price,
                fee_rate=ALPACA_FEE_PCT
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Alpaca entry failed: {e}")
            return False
    
    def _enter_kraken(self, symbol: str, price: float) -> bool:
        """Enter position on Kraken."""
        if not self.kraken:
            return False

        try:
            cash = self.kraken_status.cash
            position_value = cash * POSITION_SIZE_PCT
            qty = position_value / price

            # Fetch live per-symbol fee rate from the adapter (uses KrakenFeeTracker)
            live_fee_rate = self.kraken.get_fee_rate(symbol=symbol, is_taker=True)

            if self.dry_run:
                logger.info(
                    f"🔶 [DRY RUN] Would BUY {qty:.6f} {symbol} @ ${price:.4f}  "
                    f"fee={live_fee_rate*100:.3f}%"
                )
                self.kraken_status.position = Position(
                    exchange='kraken',
                    symbol=symbol,
                    side='long',
                    qty=qty,
                    entry_price=price,
                    entry_time=datetime.now(),
                    current_price=price,
                    fee_rate=live_fee_rate,
                )
                return True

            # Real order via adapter
            result = self.kraken.place_order(
                symbol=symbol,
                side='buy',
                qty=qty,
                order_type='market'
            )

            if result and result.get('id'):
                # Use fee_rate from the order result if present, else fall back to tracker
                actual_fee_rate = result.get('fee_rate', live_fee_rate)
                logger.info(
                    f"🟢 BOUGHT {qty:.6f} {symbol} @ ${price:.4f}  "
                    f"fee={actual_fee_rate*100:.3f}%"
                )
                self.kraken_status.position = Position(
                    exchange='kraken',
                    symbol=symbol,
                    side='long',
                    qty=qty,
                    entry_price=price,
                    entry_time=datetime.now(),
                    current_price=price,
                    fee_rate=actual_fee_rate,
                )
                return True
            else:
                logger.error(f"❌ Kraken order failed: {result}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Kraken entry failed: {e}")
            return False
    
    def exit_position(self, exchange: str, reason: str) -> Optional[float]:
        """Exit position on the specified exchange."""
        if exchange == 'alpaca':
            return self._exit_alpaca(reason)
        elif exchange == 'kraken':
            return self._exit_kraken(reason)
        return None
    
    def _exit_alpaca(self, reason: str) -> Optional[float]:
        """Exit position on Alpaca."""
        if not self.alpaca or not self.alpaca_status.position:
            return None
        
        pos = self.alpaca_status.position
        
        try:
            alpaca_symbol = pos.symbol.replace('/', '')
            
            if self.dry_run:
                # Calculate P&L
                gross_pnl = pos.unrealized_pnl
                net_pnl = pos.net_pnl_usd
                
                logger.info(f"🔶 [DRY RUN] Would SELL {pos.qty:.6f} {alpaca_symbol}")
                logger.info(f"   Reason: {reason}")
                logger.info(f"   Gross P&L: ${gross_pnl:.4f} ({pos.unrealized_pnl_pct*100:.2f}%)")
                logger.info(f"   NET P&L: ${net_pnl:.4f} ({pos.net_pnl_pct*100:.2f}%)")
                
                self.alpaca_status.position = None
                return net_pnl
            
            # Real sell
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            order = MarketOrderRequest(
                symbol=alpaca_symbol,
                qty=pos.qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            result = self.alpaca.submit_order(order)
            
            net_pnl = pos.net_pnl_usd
            logger.info(f"🔴 SOLD {pos.qty:.6f} {alpaca_symbol} | {reason} | NET: ${net_pnl:.4f}")
            
            self.alpaca_status.position = None
            return net_pnl
            
        except Exception as e:
            logger.error(f"❌ Alpaca exit failed: {e}")
            return None
    
    def _exit_kraken(self, reason: str) -> Optional[float]:
        """Exit position on Kraken."""
        if not self.kraken or not self.kraken_status.position:
            return None
        
        pos = self.kraken_status.position
        
        try:
            if self.dry_run:
                gross_pnl = pos.unrealized_pnl
                net_pnl = pos.net_pnl_usd
                
                logger.info(f"🔶 [DRY RUN] Would SELL {pos.qty:.6f} {pos.symbol}")
                logger.info(f"   Reason: {reason}")
                logger.info(f"   Gross P&L: ${gross_pnl:.4f} ({pos.unrealized_pnl_pct*100:.2f}%)")
                logger.info(f"   NET P&L: ${net_pnl:.4f} ({pos.net_pnl_pct*100:.2f}%)")
                
                self.kraken_status.position = None
                return net_pnl
            
            # Real sell via adapter
            result = self.kraken.place_order(
                symbol=pos.symbol,
                side='sell',
                qty=pos.qty,
                order_type='market'
            )
            
            if result.get('success'):
                net_pnl = pos.net_pnl_usd
                logger.info(f"🔴 SOLD {pos.qty:.6f} {pos.symbol} | {reason} | NET: ${net_pnl:.4f}")
                self.kraken_status.position = None
                return net_pnl
            else:
                logger.error(f"❌ Kraken sell failed: {result.get('error')}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Kraken exit failed: {e}")
            return None
    
    def check_position_exits(self):
        """Check if any positions should be exited."""
        # Check Alpaca position
        if self.alpaca_status.position:
            self._check_exit(self.alpaca_status, 'alpaca')
        
        # Check Kraken position
        if self.kraken_status.position:
            self._check_exit(self.kraken_status, 'kraken')
    
    def _check_exit(self, status: ExchangeStatus, exchange: str):
        """Check if a position should be exited."""
        pos = status.position
        if not pos:
            return
        
        # Update current price first
        if exchange == 'alpaca':
            self.update_alpaca_status()
        else:
            self.update_kraken_status()
        
        pos = status.position
        if not pos:
            return
        
        net_pnl_pct = pos.net_pnl_pct
        hold_mins = pos.hold_minutes
        
        # Check take profit (NET profit after fees)
        if net_pnl_pct >= TAKE_PROFIT_PCT:
            pnl = self.exit_position(exchange, f"✅ TAKE PROFIT ({net_pnl_pct*100:.2f}% net)")
            if pnl:
                self.total_trades += 1
                self.total_wins += 1
                self.total_pnl += pnl
                self._save_state()
            return
        
        # Check stop loss (gross, we still lose the fees)
        if pos.unrealized_pnl_pct <= -STOP_LOSS_PCT:
            pnl = self.exit_position(exchange, f"🛑 STOP LOSS ({pos.unrealized_pnl_pct*100:.2f}%)")
            if pnl:
                self.total_trades += 1
                self.total_pnl += pnl
                self._save_state()
            return
        
        # Check max hold time
        if hold_mins >= MAX_HOLD_MINUTES:
            pnl = self.exit_position(exchange, f"⏰ MAX HOLD ({hold_mins:.0f} min)")
            if pnl:
                self.total_trades += 1
                if pnl > 0:
                    self.total_wins += 1
                self.total_pnl += pnl
                self._save_state()
            return
    
    def print_status(self):
        """Print current status of both exchanges."""
        print("\n" + "=" * 70)
        print("🐋 ORCA DUAL HUNTER STATUS 🐋")
        print("=" * 70)
        
        # Combined stats
        total_cash = self.alpaca_status.cash + self.kraken_status.cash
        total_equity = self.alpaca_status.equity + self.kraken_status.equity
        
        print(f"\n💰 COMBINED CAPITAL:")
        print(f"   Total Cash: ${total_cash:.2f}")
        print(f"   Total Equity: ${total_equity:.2f}")
        print(f"   Session P&L: ${self.total_pnl:.4f}")
        print(f"   Trades: {self.total_trades} ({self.total_wins} wins)")
        
        # Alpaca status
        print(f"\n📊 ALPACA {'[CONNECTED]' if self.alpaca_status.connected else '[OFFLINE]'}:")
        print(f"   Cash: ${self.alpaca_status.cash:.2f}")
        print(f"   Equity: ${self.alpaca_status.equity:.2f}")
        if self.alpaca_status.position:
            pos = self.alpaca_status.position
            print(f"   Position: {pos.qty:.6f} {pos.symbol}")
            print(f"   Entry: ${pos.entry_price:.4f} | Current: ${pos.current_price:.4f}")
            print(f"   GROSS: {pos.unrealized_pnl_pct*100:+.2f}% | NET: {pos.net_pnl_pct*100:+.2f}%")
            print(f"   Hold: {pos.hold_minutes:.0f} min")
        else:
            print(f"   Position: None (hunting...)")
        
        # Kraken status
        print(f"\n🦑 KRAKEN {'[CONNECTED]' if self.kraken_status.connected else '[OFFLINE]'}:")
        print(f"   Cash: ${self.kraken_status.cash:.2f}")
        print(f"   Equity: ${self.kraken_status.equity:.2f}")
        if self.kraken_status.position:
            pos = self.kraken_status.position
            print(f"   Position: {pos.qty:.6f} {pos.symbol}")
            print(f"   Entry: ${pos.entry_price:.4f} | Current: ${pos.current_price:.4f}")
            print(f"   GROSS: {pos.unrealized_pnl_pct*100:+.2f}% | NET: {pos.net_pnl_pct*100:+.2f}%")
            print(f"   Hold: {pos.hold_minutes:.0f} min")
        else:
            print(f"   Position: None (hunting...)")
        
        # Settings reminder
        print(f"\n⚙️  SETTINGS (Fee-Aware):")
        print(f"   Take Profit: {TAKE_PROFIT_PCT*100:.1f}% gross (~{(TAKE_PROFIT_PCT-0.005)*100:.1f}% net)")
        print(f"   Stop Loss: {STOP_LOSS_PCT*100:.1f}%")
        print(f"   Max Hold: {MAX_HOLD_MINUTES} min")
        
        print("=" * 70)
    
    def run(self, scan_interval: int = 30):
        """Main hunting loop."""
        self.running = True
        logger.info("🐋 ORCA DUAL HUNTER STARTING...")
        logger.info(f"   Mode: {'DRY RUN' if self.dry_run else '🔴 LIVE TRADING'}")
        
        # Initial status update
        self.update_alpaca_status()
        self.update_kraken_status()
        self.print_status()
        
        iteration = 0
        try:
            while self.running:
                iteration += 1
                
                # Update status
                self.update_alpaca_status()
                self.update_kraken_status()
                
                # Check exits first
                self.check_position_exits()
                
                # Look for new opportunities if we have capacity
                if not self.alpaca_status.position and self.alpaca_status.connected:
                    opp = self.get_best_opportunity('alpaca')
                    if opp:
                        logger.info(f"🎯 Alpaca opportunity: {opp['symbol']} @ ${opp['price']:.4f}")
                        self.enter_position('alpaca', opp['symbol'], opp['price'])
                
                if not self.kraken_status.position and self.kraken_status.connected:
                    opp = self.get_best_opportunity('kraken')
                    if opp:
                        logger.info(f"🎯 Kraken opportunity: {opp['symbol']} @ ${opp['price']:.4f}")
                        self.enter_position('kraken', opp['symbol'], opp['price'])
                
                # Print status every 10 iterations
                if iteration % 10 == 0:
                    self.print_status()
                
                time.sleep(scan_interval)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping Orca Dual Hunter...")
            self.running = False
        
        self.print_status()
        logger.info("🐋 Orca Dual Hunter stopped.")


def main():
    """Entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Orca Dual Hunter - Trade on Alpaca & Kraken')
    parser.add_argument('--live', action='store_true', help='Enable live trading (default: dry run)')
    parser.add_argument('--interval', type=int, default=30, help='Scan interval in seconds')
    args = parser.parse_args()
    
    hunter = OrcaDualHunter(dry_run=not args.live)
    hunter.run(scan_interval=args.interval)


if __name__ == "__main__":
    main()
