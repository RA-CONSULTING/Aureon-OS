#!/usr/bin/env python3
"""
🎯 AUREON 51% LIVE - REAL-TIME KRAKEN TRADER 🎯
===============================================
ONE GOAL: 51%+ Win Rate with NET PROFIT after ALL fees
WITH COMPOUNDING using WEBSOCKET for real-time prices!

Strategy:
- Take Profit: +2.0%
- Stop Loss: -0.8%  
- Position Size: 15% of balance
- Compound profits back into balance
"""

from aureon.core.aureon_baton_link import link_system as _baton_link
import os
import sys
import json
import time
import asyncio
import websockets
from datetime import datetime, timezone
import math
from typing import Dict, List, Optional
from dataclasses import dataclass
from threading import Thread, Lock

from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client

PENNY_PROFIT_AVAILABLE = False
_penny_engine = None


def _load_penny_engine():
    """Explicitly load the optional engine only when the live loop needs it."""
    global PENNY_PROFIT_AVAILABLE, _penny_engine
    if _penny_engine is not None:
        return True
    try:
        if '/workspaces/aureon-trading' not in sys.path:
            sys.path.insert(0, '/workspaces/aureon-trading')
        from aureon.trading.penny_profit_engine import get_penny_engine
        _penny_engine = get_penny_engine()
        PENNY_PROFIT_AVAILABLE = _penny_engine is not None
    except ImportError:
        PENNY_PROFIT_AVAILABLE = False
    return PENNY_PROFIT_AVAILABLE

# �🧠 MINER BRAIN INTEGRATION
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    BRAIN_AVAILABLE = True
except ImportError:
    BRAIN_AVAILABLE = False
    print("⚠️ Miner Brain not available")

# ═══════════════════════════════════════════════════════════════
# STRATEGY PARAMETERS
# ═══════════════════════════════════════════════════════════════
# 💰 FEE MODEL: Must match penny profit formula r = ((1 + P/A) / (1-f)²) - 1
# where f = fee + slippage + spread per leg
KRAKEN_FEE = 0.0040          # 0.40% taker fee (CORRECT Kraken rate)
SLIPPAGE_PCT = 0.0020        # 0.20% estimated slippage
SPREAD_COST_PCT = 0.0010     # 0.10% estimated spread
# Combined rate per leg = 0.70% total
TOTAL_FEE_RATE = KRAKEN_FEE + SLIPPAGE_PCT + SPREAD_COST_PCT

TAKE_PROFIT_PCT = 2.0        # 2.0% profit target
STOP_LOSS_PCT = 0.8          # 0.8% stop loss
POSITION_SIZE_PCT = 0.15     # 15% of balance per trade
MAX_POSITIONS = 4            # Max concurrent positions
MIN_TRADE_USD = 15.0         # Minimum trade size
MIN_MOMENTUM = 2.0           # Minimum 24h change to enter (lowered for quiet markets)
MAX_MOMENTUM = 100.0         # Allow bigger movers
MIN_SCORE = 55               # Minimum quality score (lowered)
MIN_VOLUME = 50000           # Minimum volume for liquidity (lowered)
LOSS_STREAK_LIMIT = 3        # Max consecutive losses before blacklist
COOLDOWN_MINUTES = 13        # Fibonacci timing for cooldown

# WebSocket
KRAKEN_WS_URL = "wss://ws.kraken.com"

@dataclass
class Position:
    symbol: str
    ws_pair: str             # WebSocket pair name (e.g., "XBT/USD")
    entry_price: float
    quantity: float
    entry_fee: float
    entry_value: float
    momentum: float
    entry_time: float
    cycles: int = 0

# ═══════════════════════════════════════════════════════════════
# 🐘 ELEPHANT MEMORY - Enhanced Tracking
# ═══════════════════════════════════════════════════════════════

class ElephantMemory:
    """
    Enhanced Elephant Memory from Quantum Quackers
    Tracks hunts + results with JSONL history.
    Integrates collective intelligence from all ecosystem agents.
    """
    
    def __init__(self, filepath: str = 'elephant_live.json'):
        self.filepath = filepath
        self.history_path = filepath.replace('.json', '_history.jsonl')
        self.symbols = {} # Local memory
        self.collective_symbols = {} # Collective memory
        self.memory_sources = [
            'elephant_unified.json',
            'elephant_ultimate.json'
        ]
        self._seen_receipt_ids = set()
        self._seen_trade_ids = set()
        self.load()
    
    def load(self):
        # 1. Load local memory
        try:
            with open(self.filepath) as f:
                self.symbols = json.load(f)
        except:
            self.symbols = {}
            
        # 2. Load and aggregate collective memory
        self.collective_symbols = {}
        for source in self.memory_sources:
            if not os.path.exists(source):
                continue
            try:
                with open(source, 'r') as f:
                    data = json.load(f)
                    for sym, stats in data.items():
                        if sym not in self.collective_symbols:
                            self.collective_symbols[sym] = stats.copy()
                        else:
                            # Merge critical stats
                            s = self.collective_symbols[sym]
                            s['blacklisted'] = s.get('blacklisted', False) or stats.get('blacklisted', False)
                            s['streak'] = max(s.get('streak', 0), stats.get('streak', 0))
                            s['losses'] = s.get('losses', 0) + stats.get('losses', 0)
            except Exception as e:
                print(f"⚠️ Error loading collective memory from {source}: {e}")
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.symbols, f, indent=2)
    
    def record_hunt(self, symbol: str, volume: float = 0, change: float = 0):
        """Remember we hunted this symbol (Quackers style)"""
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'hunts': 0, 'trades': 0, 'wins': 0, 'losses': 0,
                'profit': 0, 'last_time': 0, 'streak': 0, 'blacklisted': False
            }
        
        s = self.symbols[symbol]
        s['hunts'] = s.get('hunts', 0) + 1
        s['last_time'] = time.time()
        
        # Append to JSONL history
        try:
            with open(self.history_path, 'a') as f:
                record = {
                    'ts': datetime.now().isoformat(),
                    'type': 'hunt',
                    'symbol': symbol,
                    'volume': volume,
                    'change': change
                }
                f.write(json.dumps(record) + '\n')
        except:
            pass
        
        self.save()
    
    @staticmethod
    def _no_data(blocker):
        return {
            'status': 'no_data',
            'truth_status': 'no_data',
            'generated_values': False,
            'eligible_for_learning': False,
            'blocker': blocker,
        }

    @staticmethod
    def _as_epoch(value):
        try:
            numeric = float(value)
            return numeric if math.isfinite(numeric) and numeric > 0 else None
        except (TypeError, ValueError):
            pass
        try:
            parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                return None
            numeric = parsed.timestamp()
            return numeric if math.isfinite(numeric) and numeric > 0 else None
        except (TypeError, ValueError):
            return None

    def record(self, symbol: str, receipt=None, max_age_sec: float = 300.0):
        """Persist only fresh provider-observed closed-trade receipts."""
        required = (
            'receipt_id', 'provider', 'source_id', 'source_timestamp', 'received_at',
            'terminal_status', 'trade_id', 'realized_pnl', 'fees', 'fee_currency',
            'balance_after', 'truth_status', 'generated_values', 'eligible_for_learning',
        )
        if not isinstance(receipt, dict):
            return self._no_data('missing_provider_receipt')
        missing = [key for key in required if receipt.get(key) is None]
        if missing:
            return self._no_data('missing_receipt_fields:' + ','.join(missing))
        if receipt['truth_status'] != 'real_observed' or receipt['generated_values'] is not False:
            return self._no_data('untrusted_receipt')
        if receipt['eligible_for_learning'] is not True:
            return self._no_data('not_eligible_for_learning')
        if str(receipt['terminal_status']).lower() not in {'closed', 'filled', 'settled'}:
            return self._no_data('nonterminal_receipt')
        try:
            max_age_sec = float(max_age_sec)
            realized_pnl = float(receipt['realized_pnl'])
            fees = float(receipt['fees'])
            balance_after = float(receipt['balance_after'])
        except (TypeError, ValueError):
            return self._no_data('malformed_receipt_numbers')
        if not math.isfinite(max_age_sec) or max_age_sec <= 0 or not all(
            math.isfinite(value) for value in (realized_pnl, fees, balance_after)
        ):
            return self._no_data('malformed_receipt_numbers')
        source_timestamp = self._as_epoch(receipt['source_timestamp'])
        received_at = self._as_epoch(receipt['received_at'])
        now = time.time()
        if source_timestamp is None or received_at is None:
            return self._no_data('malformed_receipt_time')
        if source_timestamp > now + 5 or received_at > now + 5:
            return self._no_data('future_receipt')
        if now - source_timestamp > max_age_sec or now - received_at > max_age_sec:
            return self._no_data('stale_receipt')
        receipt_id = str(receipt['receipt_id']).strip()
        trade_id = str(receipt['trade_id']).strip()
        if not receipt_id or not trade_id or not str(receipt['provider']).strip() or not str(receipt['source_id']).strip() or not str(receipt['fee_currency']).strip():
            return self._no_data('malformed_receipt_identity')
        if receipt_id in self._seen_receipt_ids or trade_id in self._seen_trade_ids:
            return self._no_data('duplicate_receipt_or_trade')

        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'hunts': 0, 'trades': 0, 'wins': 0, 'losses': 0,
                'profit': 0, 'last_time': 0, 'streak': 0, 'blacklisted': False
            }
        
        s = self.symbols[symbol]
        s['trades'] += 1
        s['profit'] += realized_pnl
        s['last_time'] = received_at
        
        if realized_pnl >= 0:
            s['wins'] += 1
            s['streak'] = 0
        else:
            s['losses'] += 1
            s['streak'] += 1
            if s['streak'] >= LOSS_STREAK_LIMIT:
                s['blacklisted'] = True
                print(f"🚫 {symbol} BLACKLISTED after {s['streak']} losses")
        
        # Append to JSONL history
        try:
            with open(self.history_path, 'a') as f:
                record = {
                    'type': 'provider_closed_trade',
                    'symbol': symbol,
                    'receipt_id': receipt_id,
                    'trade_id': trade_id,
                    'provider': receipt['provider'],
                    'source_id': receipt['source_id'],
                    'source_timestamp': receipt['source_timestamp'],
                    'received_at': receipt['received_at'],
                    'realized_pnl': realized_pnl,
                    'fees': fees,
                    'fee_currency': receipt['fee_currency'],
                    'balance_after': balance_after,
                }
                f.write(json.dumps(record) + '\n')
        except:
            pass
        
        self.save()
        self._seen_receipt_ids.add(receipt_id)
        self._seen_trade_ids.add(trade_id)
        return {
            'status': 'ok',
            'truth_status': 'real_observed',
            'generated_values': False,
            'eligible_for_learning': True,
            'receipt_id': receipt_id,
            'trade_id': trade_id,
        }
    
    def should_avoid(self, symbol: str) -> bool:
        # Check local memory
        if self._check_avoid(self.symbols.get(symbol)):
            return True
            
        # Check collective memory
        if self._check_avoid(self.collective_symbols.get(symbol)):
            return True
            
        return False
        
    def _check_avoid(self, s: dict) -> bool:
        if not s: return False
        
        # Blacklisted
        if s.get('blacklisted', False):
            return True
        
        # Cooldown
        if s.get('trades', 0) > 0 and time.time() - s.get('last_time', 0) < COOLDOWN_MINUTES * 60:
            return True
        
        return False


class Aureon51Live:
    """
    🎯 Real-Time WebSocket Trader for Kraken
    """
    
    def __init__(self, initial_balance: float = 1000.0, dry_run: bool = False):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.dry_run = dry_run
        self.client = get_kraken_client()
        self.memory = ElephantMemory()
        self.positions: Dict[str, Position] = {}
        self.ticker_cache: Dict[str, Dict] = {}
        self.price_history: Dict[str, List[float]] = {}
        
        # Real-time prices from WebSocket
        self.realtime_prices: Dict[str, float] = {}
        self.price_lock = Lock()
        self.ws_connected = False
        self.ws_subscribed_pairs: List[str] = []
        self.ws_task = None
        
        # Stats
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_fees = 0.0
        self.net_profit = 0.0
        self.iteration = 0
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        
        # Symbol mapping (REST API name -> WebSocket name)
        self.symbol_to_ws: Dict[str, str] = {}
        self.ws_to_symbol: Dict[str, str] = {}
        
        # 🧠 Initialize Brain
        self.brain_permission = True
        if BRAIN_AVAILABLE:
            try:
                self.brain = MinerBrain()
                print("🧠 Miner Brain initialized")
            except Exception as e:
                print(f"⚠️ Brain init failed: {e}")
                self.brain = None
        else:
            self.brain = None
        
    def banner(self):
        mode = "🧪 PAPER" if self.dry_run else "💰 LIVE"
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🎯 AUREON 51% LIVE - REAL-TIME KRAKEN TRADER 🎯                        ║
║                                                                          ║
║   Mode: {mode} TRADING                                              ║
║                                                                          ║
║   Strategy:                                                              ║
║   ├─ Take Profit: +{TAKE_PROFIT_PCT}%                                                 ║
║   ├─ Stop Loss:   -{STOP_LOSS_PCT}%                                                 ║
║   ├─ Position Size: 15% of balance (COMPOUNDING!)                     ║
║   └─ Max Positions: {MAX_POSITIONS}                                                  ║
║                                                                          ║
║   🔴 REAL-TIME WEBSOCKET PRICES                                          ║
║                                                                          ║
║   Goal: 51%+ Win Rate with NET PROFIT after fees                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
        
   💵 Starting Balance: ${self.initial_balance:.2f}
""")

    def convert_symbol_to_ws(self, symbol: str) -> str:
        """Convert REST API symbol to WebSocket pair name"""
        # Generic conversion: XXXUSD -> XXX/USD
        if symbol.endswith('USD'):
            base = symbol[:-3]
            # Handle special cases
            if base == 'XBT':
                base = 'XBT'
            return f"{base}/USD"
        return symbol
        
    async def websocket_handler(self, pairs_to_subscribe: List[str]):
        """Handle WebSocket connection and messages

        FIX #5: Exponential backoff reconnection (2s, 4s, 8s, 16s, 32s, max 60s).
        Never gives up — keeps trying forever with capped backoff.
        """
        retry_count = 0

        while True:  # Never give up — always reconnect
            try:
                async with websockets.connect(KRAKEN_WS_URL, ping_interval=20, ping_timeout=30) as ws:
                    self.ws_connected = True
                    if retry_count > 0:
                        print(f"   🟢 WebSocket RECONNECTED after {retry_count} retries!")
                    else:
                        print("   🟢 WebSocket connected!")
                    retry_count = 0

                    # Subscribe to ticker for watched pairs
                    if pairs_to_subscribe:
                        subscribe_msg = {
                            "event": "subscribe",
                            "pair": pairs_to_subscribe,
                            "subscription": {"name": "ticker"}
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        print(f"   📡 Subscribed to {len(pairs_to_subscribe)} pairs")

                    async for message in ws:
                        try:
                            data = json.loads(message)

                            # Skip system messages
                            if isinstance(data, dict):
                                if data.get('event') == 'subscriptionStatus':
                                    status = data.get('status')
                                    pair = data.get('pair', 'unknown')
                                    if status == 'subscribed':
                                        pass  # Success
                                    elif status == 'error':
                                        print(f"   ⚠️ Sub error for {pair}: {data.get('errorMessage')}")
                                continue

                            # Ticker update: [channelID, {...}, "ticker", "XBT/USD"]
                            if isinstance(data, list) and len(data) >= 4 and data[2] == "ticker":
                                ws_pair = data[3]
                                ticker_data = data[1]

                                # Get last trade price
                                if 'c' in ticker_data:
                                    price = float(ticker_data['c'][0])

                                    with self.price_lock:
                                        self.realtime_prices[ws_pair] = price

                                        # Also update by REST symbol
                                        if ws_pair in self.ws_to_symbol:
                                            symbol = self.ws_to_symbol[ws_pair]
                                            self.realtime_prices[symbol] = price

                        except Exception as e:
                            pass

            except Exception as e:
                retry_count += 1
                self.ws_connected = False
                # Exponential backoff: 2s, 4s, 8s, 16s, 32s, capped at 60s
                backoff = min(2 ** retry_count, 60)
                if retry_count <= 5:
                    print(f"   ⚠️ WebSocket error (retry {retry_count}, backoff {backoff}s): {e}")
                elif retry_count % 10 == 0:
                    print(f"   ⚠️ WebSocket still reconnecting (attempt {retry_count}, backoff {backoff}s)")
                await asyncio.sleep(backoff)
                
    def start_websocket(self, pairs: List[str]):
        """Start WebSocket in background thread"""
        # Build mapping
        ws_pairs = []
        for symbol in pairs:
            ws_pair = self.convert_symbol_to_ws(symbol)
            ws_pairs.append(ws_pair)
            self.symbol_to_ws[symbol] = ws_pair
            self.ws_to_symbol[ws_pair] = symbol
            
        self.ws_subscribed_pairs = ws_pairs
        
        def run_ws():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.websocket_handler(ws_pairs))
            
        thread = Thread(target=run_ws, daemon=True)
        thread.start()
        time.sleep(2)  # Wait for connection

    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from WebSocket"""
        with self.price_lock:
            # Try REST symbol
            if symbol in self.realtime_prices:
                return self.realtime_prices[symbol]
            # Try WS pair
            ws_pair = self.symbol_to_ws.get(symbol)
            if ws_pair and ws_pair in self.realtime_prices:
                return self.realtime_prices[ws_pair]
        return None

    def refresh_tickers(self):
        """Refresh ticker data from REST API"""
        try:
            tickers_list = self.client.get_24h_tickers()
            
            # Convert list to dict keyed by symbol
            self.ticker_cache = {}
            for t in tickers_list:
                symbol = t.get('symbol', '')
                if not symbol:
                    continue
                try:
                    price = float(t.get('lastPrice', 0))
                    change = float(t.get('priceChangePercent', 0))
                    volume = float(t.get('quoteVolume', 0))
                    
                    self.ticker_cache[symbol] = {
                        'price': price,
                        'change24h': change,
                        'volume': volume
                    }
                    
                    # Update price history
                    if symbol not in self.price_history:
                        self.price_history[symbol] = []
                    self.price_history[symbol].append(price)
                    if len(self.price_history[symbol]) > 20:
                        self.price_history[symbol] = self.price_history[symbol][-20:]
                except:
                    continue
                    
            return len(self.ticker_cache)
        except Exception as e:
            print(f"   ⚠️ Ticker refresh error: {e}")
            return 0
            
    def find_opportunities(self) -> List[Dict]:
        """Find momentum coins to trade"""
        opportunities = []
        
        for symbol, data in self.ticker_cache.items():
            # Skip stablecoins
            if symbol.endswith('USDT') or symbol.endswith('USDC'):
                continue
                
            change = data['change24h']
            price = data['price']
            volume = data['volume']
            
            # Skip if too low or TOO HIGH (super pumps are dangerous!)
            if change < MIN_MOMENTUM or change > MAX_MOMENTUM or price < 0.0001 or volume < MIN_VOLUME:
                continue
            
            # 🐘 Check Elephant Memory
            if self.memory.should_avoid(symbol):
                continue
            
            # Calculate trend from price history
            history = self.price_history.get(symbol, [])
            if len(history) >= 5:
                recent_trend = (history[-1] - history[-5]) / history[-5] * 100 if history[-5] > 0 else 0
            else:
                recent_trend = 0
            
            # Score calculation
            score = 50
            
            # Momentum score
            if change > 30: score += 25
            elif change > 20: score += 20
            elif change > 15: score += 15
            elif change > 10: score += 10
            else: score += 5
            
            # Volume score
            if volume > 1000000: score += 15
            elif volume > 500000: score += 10
            elif volume > 100000: score += 5
            
            # Recent trend bonus
            if recent_trend > 0.5: score += 10
            elif recent_trend > 0: score += 5
            
            if score >= MIN_SCORE and symbol not in self.positions:
                opportunities.append({
                    'symbol': symbol,
                    'price': price,
                    'change24h': change,
                    'volume': volume,
                    'score': score,
                    'trend': recent_trend
                })
                
        # Sort by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities[:MAX_POSITIONS - len(self.positions)]
        
    def open_position(self, opp: Dict):
        """Open a new position"""
        symbol = opp['symbol']
        price = opp['price']
        momentum = opp['change24h']
        
        # Position sizing with compounding
        pos_size = self.balance * POSITION_SIZE_PCT
        if pos_size < MIN_TRADE_USD:
            return
        
        # Entry fee uses combined rate (fee + slippage + spread) to match penny profit formula
        entry_fee = pos_size * TOTAL_FEE_RATE
        quantity = pos_size / price
        
        ws_pair = self.convert_symbol_to_ws(symbol)
        
        self.positions[symbol] = Position(
            symbol=symbol,
            ws_pair=ws_pair,
            entry_price=price,
            quantity=quantity,
            entry_fee=entry_fee,
            entry_value=pos_size,
            momentum=momentum,
            entry_time=time.time()
        )
        
        self.total_fees += entry_fee
        
        # 🐘 Record hunt
        self.memory.record_hunt(symbol, opp.get('volume', 0), momentum)
        
        # Update WS mapping
        self.symbol_to_ws[symbol] = ws_pair
        self.ws_to_symbol[ws_pair] = symbol
        
        print(f"   🎯 BUY  {symbol:12s} @ ${price:.6f} | ${pos_size:.2f} | Score: {opp['score']} | +{momentum:.1f}%")
        
    def check_positions(self):
        """Check all positions for TP/SL using real-time prices"""
        to_close = []
        
        for symbol, pos in self.positions.items():
            pos.cycles += 1
            
            # Try WebSocket price first, fall back to REST
            current_price = self.get_realtime_price(symbol)
            if current_price is None:
                current_price = self.ticker_cache.get(symbol, {}).get('price', pos.entry_price)
                
            change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            current_value = pos.quantity * current_price
            gross_pnl = current_value - pos.entry_value
            
            # 🪙 PENNY PROFIT EXIT LOGIC
            if _load_penny_engine() and _penny_engine is not None:
                action, _ = check_penny_exit('kraken', pos.entry_value, current_value)
                threshold = _penny_engine.get_threshold('kraken', pos.entry_value)
                
                if action == 'TAKE_PROFIT':
                    print(f"   🪙 PENNY TP: {symbol} | Gross: ${gross_pnl:.4f} >= Target: ${threshold.win_gte:.4f}")
                    to_close.append((symbol, "PENNY_TP", change_pct, current_price))
                elif action == 'STOP_LOSS' and pos.cycles >= 5:  # Min 5 cycles hold
                    print(f"   🪙 PENNY SL: {symbol} | Gross: ${gross_pnl:.4f} <= Stop: ${threshold.stop_lte:.4f}")
                    to_close.append((symbol, "PENNY_SL", change_pct, current_price))
            else:
                # Fallback to percentage exits
                if change_pct >= TAKE_PROFIT_PCT:
                    to_close.append((symbol, "TP", change_pct, current_price))
                elif change_pct <= -STOP_LOSS_PCT and pos.cycles >= 5:
                    to_close.append((symbol, "SL", change_pct, current_price))
                
        for symbol, reason, pct, price in to_close:
            self.close_position(symbol, reason, pct, price)
            
    def close_position(self, symbol: str, reason: str, pct: float, price: float):
        """Close a position"""
        pos = self.positions.pop(symbol)
        
        # Calculate P&L using combined rate (fee + slippage + spread)
        # This matches the penny profit formula: r = ((1 + P/A) / (1-f)²) - 1
        exit_value = pos.quantity * price
        exit_fee = exit_value * TOTAL_FEE_RATE
        gross_pnl = exit_value - pos.entry_value
        
        # Total expenses = entry_fee + exit_fee (both use combined rate)
        total_expenses = pos.entry_fee + exit_fee
        net_pnl = gross_pnl - total_expenses
        
        self.total_fees += exit_fee
        self.balance += net_pnl
        self.net_profit += net_pnl
        self.total_trades += 1
        
        # 🐘 Record result
        self.memory.record(symbol)
        
        if net_pnl > 0:
            self.wins += 1
            icon = "✅"
            # 🇮🇪 IRA SNIPER CELEBRATION!
            import random
            IRA_QUOTES = [
                "Our revenge will be the laughter of our children. - Bobby Sands 🍀",
                "Tiocfaidh ár lá! - Our day will come!",
                "The Republic still lives! - Bobby Sands",
                "Financial freedom IS freedom. Penny by penny, we rise! 💰",
            ]
            quote = random.choice(IRA_QUOTES)
            print(f"\n🇮🇪🇮🇪🇮🇪 IRA SNIPER WIN! 🇮🇪🇮🇪🇮🇪")
            print(f"    💰 +${net_pnl:.4f} on {symbol}")
            print(f"    📜 \"{quote}\"")
            print(f"🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪🇮🇪\n")
        else:
            self.losses += 1
            icon = "❌"
            
        # Track drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        dd = (self.peak_balance - self.balance) / self.peak_balance * 100
        if dd > self.max_drawdown:
            self.max_drawdown = dd
            
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        
        print(f"   {icon} CLOSE {symbol:12s} | {reason} {pct:+.2f}% | Net: ${net_pnl:+.2f} | Bal: ${self.balance:.2f} | WR: {win_rate:.1f}%")
        
    def run(self):
        """Main trading loop"""
        self.banner()
        
        print("🎯 Connecting to Kraken...")
        pair_count = self.refresh_tickers()
        print(f"✅ Connected! {pair_count} pairs")
        
        # Find initial opportunities to subscribe to
        initial_opps = self.find_opportunities()
        symbols_to_watch = [o['symbol'] for o in initial_opps[:10]]
        
        # Add some major pairs
        major_pairs = ['ETHUSD', 'SOLUSD', 'XBTUSD', 'ADAUSD', 'DOTUSD']
        for p in major_pairs:
            if p not in symbols_to_watch and p in self.ticker_cache:
                symbols_to_watch.append(p)
                
        # Start WebSocket for real-time prices
        print(f"\n🔴 Starting real-time WebSocket feed for {len(symbols_to_watch)} pairs...")
        self.start_websocket(symbols_to_watch)
        
        interval = int(os.environ.get('INTERVAL', 5))
        
        try:
            while True:
                self.iteration += 1
                now = datetime.now().strftime("%H:%M:%S")
                
                print(f"\n{'━'*70}")
                print(f"🔄 Cycle {self.iteration} - {now}")
                print(f"{'━'*70}")
                
                # 🧠 BRAIN CYCLE
                if self.brain and self.iteration % 10 == 1:
                    try:
                        print("\n🧠 Consulting Miner Brain...")
                        self.brain.run_cycle()
                        pred = self.brain.get_latest_prediction()
                        if pred:
                            print(f"   Brain says: {pred['direction']} (Conf: {pred['confidence']}%)")
                            if pred['direction'] == 'BEARISH' and pred['confidence'] > 70:
                                print("   🛑 Brain VETO: Market too bearish")
                                self.brain_permission = False
                            else:
                                self.brain_permission = True
                            
                            if hasattr(self.brain, 'dream_engine'):
                                # Pass default values: 0.0 change, 50 F&G
                                dream = self.brain.dream_engine.get_prepared_response(0.0, 50)
                                if dream:
                                    print(f"   💭 Dream: {dream['action']}")
                                    if dream['action'] in ['EXIT_NOW', 'WAIT_FOR_CLARITY']:
                                        self.brain_permission = False
                    except Exception as e:
                        print(f"   ⚠️ Brain error: {e}")
                
                # Refresh REST API data
                self.refresh_tickers()
                
                # Check existing positions with real-time prices
                self.check_positions()
                
                # Find and open new positions
                if len(self.positions) < MAX_POSITIONS and self.brain_permission:
                    opps = self.find_opportunities()
                    if opps:
                        print(f"\n   🔮 Opportunities:")
                        for opp in opps[:5]:
                            print(f"      {opp['symbol']:12s} +{opp['change24h']:.1f}% | Score: {opp['score']}")
                    
                    for opp in opps[:MAX_POSITIONS - len(self.positions)]:
                        self.open_position(opp)
                        
                # Show active positions with real-time prices
                if self.positions:
                    print(f"\n   📊 Active Positions:")
                    for symbol, pos in self.positions.items():
                        rt_price = self.get_realtime_price(symbol)
                        if rt_price:
                            pct = (rt_price - pos.entry_price) / pos.entry_price * 100
                            src = "🔴RT"
                        else:
                            cached = self.ticker_cache.get(symbol, {}).get('price', pos.entry_price)
                            pct = (cached - pos.entry_price) / pos.entry_price * 100
                            src = "REST"
                        print(f"      {symbol:12s} Entry: ${pos.entry_price:.6f} | Now: {pct:+.2f}% [{src}]")
                        
                # Stats
                win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
                rt_count = len(self.realtime_prices)
                print(f"\n   💎 ${self.balance:.2f} | Trades: {self.total_trades} | WR: {win_rate:.1f}% | WS: {'🟢' if self.ws_connected else '🔴'} ({rt_count} prices)")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🎯 Stopping...")
            self.final_report()
            
    def final_report(self):
        """Print final statistics"""
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║              🎯 AUREON 51% LIVE - FINAL REPORT 🎯                        ║
╚══════════════════════════════════════════════════════════════════════════╝

   Starting:    ${self.initial_balance:.2f}
   Final:       ${self.balance:.2f}
   💰 NET P&L:  ${self.balance - self.initial_balance:+.2f} ({total_return:+.2f}%)

   Trades:      {self.total_trades}
   Wins:        {self.wins}
   Losses:      {self.losses}
   🎯 WIN RATE: {win_rate:.1f}%

   Total Fees:  ${self.total_fees:.2f}
   Net Profit:  ${self.net_profit:+.2f}
   Max DD:      {self.max_drawdown:.1f}%
""")


if __name__ == "__main__":
    dry_run = os.environ.get('LIVE', '0') != '1'
    balance = float(os.environ.get('BALANCE', 1000))
    
    trader = Aureon51Live(initial_balance=balance, dry_run=dry_run)
    trader.run()
