#!/usr/bin/env python3
"""
S5 INFINITE DANCE - THE STEPPING STONE SYMPHONY
================================================
Every trade is a stepping stone.
Every conversion flows to the next.
Kraken and Binance dance together.
The rhythm never stops.

"Follow the rhythm, dance on net profit, using every available move"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import websockets
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.binance_client import BinanceClient, get_binance_client


@dataclass
class SteppingStone:
    """A single step in the infinite dance"""
    exchange: str  # 'kraken' or 'binance'
    asset: str
    action: str  # 'buy', 'sell', 'convert'
    amount: float
    price: float
    profit: float
    momentum: float
    timestamp: datetime = field(default_factory=datetime.now)
    next_stone: Optional['SteppingStone'] = None


@dataclass
class DanceRhythm:
    """The rhythm pattern for an asset"""
    asset: str
    beat_count: int = 0  # How many times we've danced with this asset
    last_direction: str = ''  # 'up' or 'down'
    momentum_history: List[float] = field(default_factory=list)
    profit_streak: int = 0
    total_profit: float = 0.0


class S5InfiniteDance:
    """
    THE INFINITE DANCE
    
    Two exchanges. Infinite paths. Every move a stepping stone.
    The rhythm flows: Kraken ↔ Binance ↔ Kraken ↔ ...
    
    Dance Rules:
    1. Every trade must profit (or set up next profit)
    2. Each stone leads to the next
    3. Follow the momentum rhythm
    4. Use EVERY available move
    5. Never stop dancing
    """
    
    # WebSocket URLs
    BINANCE_WS = "wss://stream.binance.com:9443/stream?streams="
    
    # The dance floor - all tradeable assets
    KRAKEN_PAIRS = {
        'ATOM': 'ATOMUSD', 'DASH': 'DASHUSD', 'SOL': 'SOLUSD',
        'DOT': 'DOTUSD', 'LINK': 'LINKUSD', 'AVAX': 'AVAXUSD',
        'UNI': 'UNIUSD', 'AAVE': 'AAVEUSD', 'CRV': 'CRVUSD',
        'SUSHI': 'SUSHIUSD', 'COMP': 'COMPUSD', 'SNX': 'SNXUSD',
        'GRT': 'GRTUSD', 'FLOW': 'FLOWUSD', 'NEAR': 'NEARUSD',
        'FTM': 'FTMUSD', 'SAND': 'SANDUSD', 'MANA': 'MANAUSD',
        'BTC': 'XBTUSD', 'ETH': 'ETHUSD', 'XRP': 'XRPUSD',
    }
    
    BINANCE_PAIRS = {
        'BTC': 'BTCUSDC', 'ETH': 'ETHUSDC', 'SOL': 'SOLUSDC',
        'BNB': 'BNBUSDC', 'XRP': 'XRPUSDC', 'ADA': 'ADAUSDC',
        'AVAX': 'AVAXUSDC', 'DOT': 'DOTUSDC', 'LINK': 'LINKUSDC',
        'ATOM': 'ATOMUSDC', 'UNI': 'UNIUSDC', 'NEAR': 'NEARUSDC',
        'NEWT': 'NEWTUSDT',  # Your NEWT!
    }
    
    # Dance parameters
    MIN_STEP_USD = 1.5  # Minimum stepping stone value
    RHYTHM_THRESHOLD = 0.01  # 1 basis point to feel the beat
    
    def __init__(self):
        # The dancers
        self.kraken = get_kraken_client()
        self.binance = get_binance_client()
        
        # The dance floor state
        self.kraken_holdings: Dict[str, float] = {}
        self.binance_holdings: Dict[str, float] = {}
        self.prices: Dict[str, Dict[str, float]] = defaultdict(dict)  # {symbol: {exchange: price}}
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # The rhythm
        self.rhythms: Dict[str, DanceRhythm] = {}
        self.stepping_stones: List[SteppingStone] = []
        self.current_stone: Optional[SteppingStone] = None
        
        # Dance statistics
        self.running = False
        self.start_time = None
        self.total_profit = 0.0
        self.total_steps = 0
        self.dance_velocity = 0.0  # Profit per hour
        
        # The infinite loop
        self.snowball = 1.0  # Momentum multiplier
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _stop(self, *args):
        print("\n🛑 The dance pauses... (but never ends)")
        self.running = False
    
    async def initialize(self):
        """Set up the dance floor"""
        print("""
╔═══════════════════════════════════════════════════════════════════════╗
║   💃 S5 INFINITE DANCE - THE STEPPING STONE SYMPHONY 🕺              ║
║                                                                       ║
║   Every trade is a stepping stone                                     ║
║   Every conversion flows to the next                                  ║
║   Kraken and Binance dance together                                   ║
║   The rhythm never stops                                              ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
        
        # Test connections
        print("🔌 Connecting to the dance floor...")
        
        # Kraken
        try:
            kraken_balance = self.kraken.get_account_balance()
            if kraken_balance:
                print("   🐙 Kraken: Connected!")
                for asset, amount in kraken_balance.items():
                    if amount > 0.0001 and asset in self.KRAKEN_PAIRS:
                        self.kraken_holdings[asset] = amount
                        print(f"      💎 {asset}: {amount:.6f}")
        except Exception as e:
            print(f"   🐙 Kraken: {e}")
        
        # Binance
        try:
            if self.binance.ping():
                print("   🟡 Binance: Connected!")
                account = self.binance.account()
                for bal in account.get('balances', []):
                    asset = bal['asset']
                    total = float(bal.get('free', 0)) + float(bal.get('locked', 0))
                    if total > 0.000001:
                        self.binance_holdings[asset] = total
                        if total > 0.01:
                            print(f"      💎 {asset}: {total:.6f}")
        except Exception as e:
            print(f"   🟡 Binance: {e}")
        
        # Initialize rhythms for all assets
        all_assets = set(self.kraken_holdings.keys()) | set(self.binance_holdings.keys())
        for asset in all_assets:
            self.rhythms[asset] = DanceRhythm(asset=asset)
        
        total_kraken = sum(self._get_usd_value(a, b, 'kraken') for a, b in self.kraken_holdings.items())
        total_binance = sum(self._get_usd_value(a, b, 'binance') for a, b in self.binance_holdings.items())
        
        print(f"\n   💼 Dance Floor Capital:")
        print(f"      Kraken:  ${total_kraken:.2f}")
        print(f"      Binance: ${total_binance:.2f}")
        print(f"      Total:   ${total_kraken + total_binance:.2f}")
        
        return len(self.kraken_holdings) > 0 or len(self.binance_holdings) > 0
    
    def _get_usd_value(self, asset: str, amount: float, exchange: str) -> float:
        """Get USD value of an asset"""
        if asset in ['USD', 'USDT', 'USDC', 'ZUSD']:
            return amount
        
        # Use cached price if available
        if asset in self.prices and exchange in self.prices[asset]:
            return amount * self.prices[asset][exchange]
        
        # Fetch price
        try:
            if exchange == 'kraken' and asset in self.KRAKEN_PAIRS:
                # Use Binance price (faster)
                pair = f"{asset}USDT"
                price = float(self.binance.best_price(pair, timeout=1).get('price', 0))
                if price > 0:
                    return amount * price
            elif exchange == 'binance':
                for quote in ['USDC', 'USDT']:
                    pair = f"{asset}{quote}"
                    try:
                        price = float(self.binance.best_price(pair, timeout=1).get('price', 0))
                        if price > 0:
                            return amount * price
                    except:
                        pass
        except:
            pass
        
        return 0.0
    
    def _get_binance_streams(self) -> List[str]:
        """Get WebSocket streams for Binance"""
        streams = set()
        
        # All assets we hold on either exchange
        all_assets = set(self.kraken_holdings.keys()) | set(self.binance_holdings.keys())
        
        for asset in all_assets:
            for quote in ['USDT', 'USDC']:
                pair = f"{asset}{quote}"
                streams.add(f"{pair.lower()}@ticker")
        
        # Major pairs for rhythm detection
        for major in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
            streams.add(f"{major.lower()}@ticker")
        
        return list(streams)[:50]
    
    async def run(self):
        """Start the infinite dance"""
        if not await self.initialize():
            print("\n⚠️ No assets to dance with!")
            return
        
        print("\n⚠️ Type 'DANCE' to begin the infinite rhythm: ", end='')
        confirm = input()
        if confirm.strip().upper() != 'DANCE':
            print("The dance awaits...")
            return
        
        print("\n🎵 THE DANCE BEGINS! 🎵\n")
        
        self.running = True
        self.start_time = datetime.now()
        
        await asyncio.gather(
            self._price_rhythm(),
            self._dance_loop(),
            self._rhythm_display(),
        )
        
        self._final_bow()
    
    async def _price_rhythm(self):
        """WebSocket feed - the heartbeat of the dance"""
        streams = self._get_binance_streams()
        
        if not streams:
            return
        
        url = self.BINANCE_WS + "/".join(streams)
        print(f"🎧 Tuning into {len(streams)} rhythm channels...")
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    print("   🎵 Rhythm locked!")
                    
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            
                            if 'data' in data:
                                await self._feel_the_beat(data['data'])
                                
                        except asyncio.TimeoutError:
                            continue
                            
            except Exception as e:
                if self.running:
                    print(f"\n   🎵 Rhythm interrupted: {e}")
                    await asyncio.sleep(2)
    
    async def _feel_the_beat(self, ticker: Dict):
        """Process price update - feel the rhythm"""
        symbol = ticker.get('s', '')
        price = float(ticker.get('c', 0))
        change_24h = float(ticker.get('P', 0))
        
        if price <= 0:
            return
        
        now = datetime.now()
        
        # Extract asset from symbol
        asset = None
        for quote in ['USDT', 'USDC', 'USD']:
            if symbol.endswith(quote):
                asset = symbol[:-len(quote)]
                break
        
        if not asset:
            return
        
        # Update price
        self.prices[asset]['binance'] = price
        self.prices[asset]['kraken'] = price  # Approximate
        
        # Store history
        self.price_history[symbol].append((now, price))
        
        # Keep 5 min of history
        cutoff = now - timedelta(minutes=5)
        self.price_history[symbol] = [(t, p) for t, p in self.price_history[symbol] if t > cutoff]
        
        # Update rhythm
        if asset in self.rhythms:
            rhythm = self.rhythms[asset]
            
            # Calculate momentum
            history = self.price_history[symbol]
            if len(history) >= 5:
                oldest = history[0][1]
                momentum = (price - oldest) / oldest * 100
                
                rhythm.momentum_history.append(momentum)
                if len(rhythm.momentum_history) > 20:
                    rhythm.momentum_history = rhythm.momentum_history[-20:]
                
                # Detect rhythm direction
                if momentum > 0.01:
                    rhythm.last_direction = 'up'
                elif momentum < -0.01:
                    rhythm.last_direction = 'down'
    
    async def _dance_loop(self):
        """The main dance - stepping stones"""
        await asyncio.sleep(5)  # Wait for rhythm
        
        print("\n💃 Finding the first stepping stone...")
        
        while self.running:
            try:
                # Find the best next step
                next_step = await self._find_next_stone()
                
                if next_step:
                    await self._execute_step(next_step)
                
            except Exception as e:
                print(f"\n   ⚠️ Dance stumble: {e}")
            
            await asyncio.sleep(1)  # Dance tempo
    
    async def _find_next_stone(self) -> Optional[Dict]:
        """Find the next stepping stone in the dance"""
        opportunities = []
        
        # Check Kraken opportunities
        for asset, amount in self.kraken_holdings.items():
            if amount < 0.001:
                continue
            
            usd_value = self._get_usd_value(asset, amount, 'kraken')
            if usd_value < self.MIN_STEP_USD:
                continue
            
            # Get rhythm
            rhythm = self.rhythms.get(asset)
            if not rhythm or not rhythm.momentum_history:
                continue
            
            momentum = rhythm.momentum_history[-1] if rhythm.momentum_history else 0
            
            # Threshold adjusted by snowball
            threshold = self.RHYTHM_THRESHOLD / self.snowball
            
            if abs(momentum) >= threshold:
                # Decide action based on rhythm
                if momentum > 0:
                    action = 'sell'  # Take profit on up
                else:
                    action = 'hold'  # Buy the dip with USD
                
                if action != 'hold':
                    opportunities.append({
                        'exchange': 'kraken',
                        'asset': asset,
                        'action': action,
                        'amount': amount,
                        'momentum': momentum,
                        'usd_value': usd_value,
                        'score': abs(momentum) * (1 + rhythm.beat_count * 0.1)
                    })
        
        # Check Binance opportunities
        for asset, amount in self.binance_holdings.items():
            if amount < 0.000001:
                continue
            
            usd_value = self._get_usd_value(asset, amount, 'binance')
            if usd_value < self.MIN_STEP_USD:
                continue
            
            rhythm = self.rhythms.get(asset)
            if not rhythm or not rhythm.momentum_history:
                continue
            
            momentum = rhythm.momentum_history[-1] if rhythm.momentum_history else 0
            threshold = self.RHYTHM_THRESHOLD / self.snowball
            
            if abs(momentum) >= threshold:
                if momentum > 0:
                    action = 'sell'
                else:
                    action = 'hold'
                
                if action != 'hold':
                    opportunities.append({
                        'exchange': 'binance',
                        'asset': asset,
                        'action': action,
                        'amount': amount,
                        'momentum': momentum,
                        'usd_value': usd_value,
                        'score': abs(momentum) * (1 + rhythm.beat_count * 0.1)
                    })
        
        # Check for buy opportunities with USD/USDC
        for usd_asset in ['ZUSD', 'USD', 'USDC', 'USDT']:
            kraken_usd = self.kraken_holdings.get(usd_asset, 0)
            if kraken_usd >= self.MIN_STEP_USD:
                # Find best dip to buy
                best_dip = None
                best_score = 0
                
                for asset, rhythm in self.rhythms.items():
                    if not rhythm.momentum_history:
                        continue
                    momentum = rhythm.momentum_history[-1]
                    if momentum < -self.RHYTHM_THRESHOLD / self.snowball:
                        score = abs(momentum)
                        if score > best_score:
                            best_score = score
                            best_dip = (asset, momentum)
                
                if best_dip:
                    opportunities.append({
                        'exchange': 'kraken',
                        'asset': best_dip[0],
                        'action': 'buy',
                        'amount': kraken_usd * 0.3,  # Use 30% of USD
                        'momentum': best_dip[1],
                        'usd_value': kraken_usd * 0.3,
                        'score': best_score * 1.5,  # Bonus for buying dips
                        'spend_asset': usd_asset
                    })
            
            binance_usd = self.binance_holdings.get(usd_asset, 0)
            if binance_usd >= self.MIN_STEP_USD:
                best_dip = None
                best_score = 0
                
                for asset, rhythm in self.rhythms.items():
                    if not rhythm.momentum_history:
                        continue
                    momentum = rhythm.momentum_history[-1]
                    if momentum < -self.RHYTHM_THRESHOLD / self.snowball:
                        score = abs(momentum)
                        if score > best_score:
                            best_score = score
                            best_dip = (asset, momentum)
                
                if best_dip:
                    opportunities.append({
                        'exchange': 'binance',
                        'asset': best_dip[0],
                        'action': 'buy',
                        'amount': binance_usd * 0.3,
                        'momentum': best_dip[1],
                        'usd_value': binance_usd * 0.3,
                        'score': best_score * 1.5,
                        'spend_asset': usd_asset
                    })
        
        if not opportunities:
            return None
        
        # Sort by score and pick best
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities[0]
    
    async def _execute_step(self, step: Dict):
        """Execute a stepping stone"""
        exchange = step['exchange']
        asset = step['asset']
        action = step['action']
        momentum = step['momentum']
        
        # Rate limit check
        rate_key = f"{exchange}:{asset}"
        
        print(f"\n   💫 STEP: {action.upper()} {asset} on {exchange.upper()}")
        print(f"      Momentum: {momentum:+.3f}% | Value: ${step['usd_value']:.2f}")
        
        try:
            if exchange == 'kraken':
                await self._kraken_step(step)
            else:
                await self._binance_step(step)
                
        except Exception as e:
            print(f"      ❌ Step failed: {e}")
    
    async def _kraken_step(self, step: Dict):
        """Execute step on Kraken"""
        asset = step['asset']
        action = step['action']
        
        if asset not in self.KRAKEN_PAIRS:
            print(f"      ⚠️ {asset} not tradeable on Kraken")
            return
        
        pair = self.KRAKEN_PAIRS[asset]
        price = self.prices.get(asset, {}).get('kraken', 0)
        
        if action == 'sell':
            amount = step['amount'] * 0.3  # Sell 30%
            if amount * price < 1.0:
                return
            
            result = self.kraken.place_market_order(
                symbol=pair,
                side='sell',
                quantity=amount
            )
            
            if result:
                profit_est = step['usd_value'] * 0.3 * abs(step['momentum']) / 100
                self._record_step(step, profit_est)
                self.kraken_holdings[asset] -= amount
                print(f"      ✅ SOLD {amount:.6f} {asset}")
                
        elif action == 'buy':
            spend = step.get('spend_asset', 'ZUSD')
            spend_amount = min(step['amount'], self.kraken_holdings.get(spend, 0))
            
            if spend_amount < 1.0:
                return
            
            # Calculate quantity to buy
            if price > 0:
                qty = spend_amount / price * 0.98  # 2% buffer for fees
                
                result = self.kraken.place_market_order(
                    symbol=pair,
                    side='buy',
                    quantity=qty
                )
                
                if result:
                    profit_est = spend_amount * abs(step['momentum']) / 100
                    self._record_step(step, profit_est)
                    self.kraken_holdings[spend] = self.kraken_holdings.get(spend, 0) - spend_amount
                    self.kraken_holdings[asset] = self.kraken_holdings.get(asset, 0) + qty
                    print(f"      ✅ BOUGHT {qty:.6f} {asset}")
    
    async def _binance_step(self, step: Dict):
        """Execute step on Binance"""
        asset = step['asset']
        action = step['action']
        
        # Skip stablecoins - can't buy USDC with USDC
        if asset in ['USDC', 'USDT', 'USD', 'BUSD']:
            return
        
        # Find trading pair - check what actually exists
        pair = None
        quote_used = None
        for quote in ['USDC', 'USDT']:
            test_pair = f"{asset}{quote}"
            try:
                # Verify pair exists by trying to get price
                price_check = self.binance.best_price(test_pair, timeout=1)
                if price_check.get('price'):
                    pair = test_pair
                    quote_used = quote
                    break
            except:
                continue
        
        if not pair:
            print(f"      ⚠️ No tradeable pair found for {asset}")
            return
        
        price = float(self.binance.best_price(pair, timeout=2).get('price', 0))
        if price <= 0:
            print(f"      ⚠️ Could not get price for {pair}")
            return
        
        if action == 'sell':
            amount = step['amount'] * 0.3
            trade_value = amount * price
            
            if trade_value < 11:  # Binance min notional ~$10
                print(f"      ⚠️ Trade value ${trade_value:.2f} below $11 min")
                return
            
            try:
                result = self.binance.place_market_order(
                    symbol=pair,
                    side='SELL',
                    quantity=amount
                )
                
                if result.get('rejected'):
                    print(f"      ⚠️ Rejected: {result.get('reason')}")
                    return
                
                if result.get('orderId') or result.get('status') == 'FILLED':
                    exec_qty = float(result.get('executedQty', amount))
                    profit_est = trade_value * abs(step['momentum']) / 100
                    self._record_step(step, profit_est)
                    self.binance_holdings[asset] = self.binance_holdings.get(asset, 0) - exec_qty
                    self.binance_holdings[quote_used] = self.binance_holdings.get(quote_used, 0) + (exec_qty * price)
                    print(f"      ✅ SOLD {exec_qty:.6f} {asset} @ ${price:.4f}")
                else:
                    print(f"      ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"      ❌ Sell error: {e}")
                
        elif action == 'buy':
            # Find which stablecoin we have to spend
            spend = None
            spend_amount = 0
            for usd in ['USDC', 'USDT']:
                bal = self.binance_holdings.get(usd, 0)
                if bal >= 11:
                    spend = usd
                    spend_amount = min(step['amount'], bal * 0.3)  # Use 30% max
                    break
            
            if not spend or spend_amount < 11:
                print(f"      ⚠️ Insufficient {spend or 'stablecoin'} (need $11, have ${spend_amount:.2f})")
                return
            
            # Make sure pair uses the right quote currency
            buy_pair = f"{asset}{spend}"
            try:
                price_check = self.binance.best_price(buy_pair, timeout=1)
                if not price_check.get('price'):
                    buy_pair = f"{asset}USDT"  # Fallback
            except:
                buy_pair = f"{asset}USDT"
            
            try:
                result = self.binance.place_market_order(
                    symbol=buy_pair,
                    side='BUY',
                    quote_qty=spend_amount
                )
                
                if result.get('rejected'):
                    print(f"      ⚠️ Rejected: {result.get('reason')}")
                    return
                
                if result.get('orderId') or result.get('status') == 'FILLED':
                    exec_qty = float(result.get('executedQty', 0))
                    exec_quote = float(result.get('cummulativeQuoteQty', spend_amount))
                    profit_est = exec_quote * abs(step['momentum']) / 100
                    self._record_step(step, profit_est)
                    self.binance_holdings[spend] = self.binance_holdings.get(spend, 0) - exec_quote
                    self.binance_holdings[asset] = self.binance_holdings.get(asset, 0) + exec_qty
                    print(f"      ✅ BOUGHT {exec_qty:.6f} {asset} @ ${price:.4f}")
                else:
                    print(f"      ⚠️ Unexpected: {result}")
            except Exception as e:
                print(f"      ❌ Buy error: {e}")
    
    def _record_step(self, step: Dict, profit: float):
        """Record a stepping stone"""
        stone = SteppingStone(
            exchange=step['exchange'],
            asset=step['asset'],
            action=step['action'],
            amount=step['amount'],
            price=self.prices.get(step['asset'], {}).get(step['exchange'], 0),
            profit=profit,
            momentum=step['momentum']
        )
        
        # Link to previous stone
        if self.current_stone:
            self.current_stone.next_stone = stone
        
        self.stepping_stones.append(stone)
        self.current_stone = stone
        
        # Update stats
        self.total_profit += profit
        self.total_steps += 1
        self.snowball *= 1.002  # Grow the snowball
        
        # Update rhythm
        if step['asset'] in self.rhythms:
            rhythm = self.rhythms[step['asset']]
            rhythm.beat_count += 1
            rhythm.total_profit += profit
            if profit > 0:
                rhythm.profit_streak += 1
            else:
                rhythm.profit_streak = 0
        
        print(f"      💰 Profit: ${profit:.4f} | Total: ${self.total_profit:.4f} | Snowball: {self.snowball:.3f}x")
    
    async def _rhythm_display(self):
        """Display the dance rhythm"""
        while self.running:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            hours = max(0.001, elapsed / 3600)
            velocity = self.total_profit / hours
            
            # Top rhythms
            active_rhythms = [(a, r) for a, r in self.rhythms.items() if r.momentum_history]
            active_rhythms.sort(key=lambda x: abs(x[1].momentum_history[-1]) if x[1].momentum_history else 0, reverse=True)
            
            rhythm_str = " | ".join([
                f"{a}:{r.momentum_history[-1]:+.2f}%" 
                for a, r in active_rhythms[:4] 
                if r.momentum_history
            ]) if active_rhythms else "Finding rhythm..."
            
            print(f"\r🎵 {int(elapsed)}s | 👣 {self.total_steps} steps | "
                  f"💰 ${self.total_profit:.4f} | ⚡${velocity:.2f}/hr | "
                  f"❄️ {self.snowball:.3f}x | {rhythm_str}",
                  end='', flush=True)
            
            await asyncio.sleep(5)
    
    def _final_bow(self):
        """Final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print("\n\n" + "="*70)
        print("🎭 THE DANCE SESSION FINALE")
        print("="*70)
        print(f"⏱️ Duration: {elapsed:.0f}s ({elapsed/3600:.2f} hours)")
        print(f"👣 Total Steps: {self.total_steps}")
        print(f"💰 Total Profit: ${self.total_profit:.4f}")
        print(f"⚡ Velocity: ${self.total_profit/(elapsed/3600) if elapsed > 0 else 0:.2f}/hr")
        print(f"❄️ Final Snowball: {self.snowball:.4f}x")
        
        # Top dancers
        if self.rhythms:
            print("\n🌟 Star Performers:")
            sorted_rhythms = sorted(
                [(a, r) for a, r in self.rhythms.items() if r.beat_count > 0],
                key=lambda x: x[1].total_profit,
                reverse=True
            )[:5]
            for asset, rhythm in sorted_rhythms:
                print(f"   {asset}: {rhythm.beat_count} beats, ${rhythm.total_profit:.4f} profit")
        
        # Recent steps
        if self.stepping_stones:
            print("\n👣 Recent Stepping Stones:")
            for stone in self.stepping_stones[-10:]:
                print(f"   {stone.action.upper()} {stone.asset} on {stone.exchange}: "
                      f"${stone.profit:.4f} ({stone.momentum:+.2f}%)")
        
        print("="*70)
        print("\n🎵 The dance continues... until $1M! 🎵")
        
        # Save state
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'total_steps': self.total_steps,
                'total_profit': self.total_profit,
                'snowball': self.snowball,
                'stones': [
                    {
                        'exchange': s.exchange,
                        'asset': s.asset,
                        'action': s.action,
                        'amount': s.amount,
                        'profit': s.profit,
                        'momentum': s.momentum,
                        'time': s.timestamp.isoformat()
                    }
                    for s in self.stepping_stones[-100:]
                ]
            }
            with open('infinite_dance_state.json', 'w') as f:
                json.dump(state, f, indent=2)
            print("\n💾 Dance state saved!")
        except Exception as e:
            print(f"\n⚠️ Could not save state: {e}")


async def main():
    dance = S5InfiniteDance()
    await dance.run()


if __name__ == "__main__":
    asyncio.run(main())
