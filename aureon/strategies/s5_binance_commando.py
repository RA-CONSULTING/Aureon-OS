#!/usr/bin/env python3
"""
S5 BINANCE CONVERSION COMMANDO
==============================
Fast, aggressive spot trading across Binance ecosystem.

Features:
- Real-time price feeds for 100+ pairs
- Instant spot market orders
- Cross-conversion (BTC→ETH→SOL paths)
- UK compliance built-in
- Snowball momentum

Run with --dry-run for simulation
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import websockets
import signal
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aureon.exchanges.binance_client import BinanceClient, get_binance_client


class BinanceConversionCommando:
    """
    AGGRESSIVE BINANCE SPOT TRADER
    
    Scans all your holdings.
    Finds momentum.
    Executes conversions.
    Prints money.
    """
    
    WS_URL = "wss://stream.binance.com:9443/stream?streams="
    
    # Major quote currencies
    QUOTES = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP']
    
    # Minimum trade value
    MIN_VALUE_USD = 11.0
    
    # Trigger threshold (basis points)
    MIN_MOVE_BPS = 5  # 0.05%
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        os.environ['BINANCE_DRY_RUN'] = 'true' if dry_run else 'false'
        
        self.binance = get_binance_client()
        
        # State
        self.holdings: Dict[str, float] = {}
        self.prices: Dict[str, List] = defaultdict(list)
        self.current_prices: Dict[str, Dict] = {}
        self.tradeable_pairs: Set[str] = set()
        self.pair_info: Dict[str, Dict] = {}
        
        # Trading
        self.last_trade: Dict[str, datetime] = {}
        self.cooldown_secs = 30
        self.snowball = 1.0
        
        # Stats
        self.running = False
        self.start_time = None
        self.trades = 0
        self.profit = 0.0
        self.trade_log = []
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _stop(self, *args):
        print("\n🛑 Stopping...")
        self.running = False
    
    def load_pairs(self):
        """Load tradeable pairs"""
        print("\n📊 Loading Binance pairs...")
        
        try:
            info = self.binance.exchange_info()
            
            for sym in info.get('symbols', []):
                if sym.get('status') != 'TRADING':
                    continue
                if not sym.get('isSpotTradingAllowed', False):
                    continue
                
                pair = sym['symbol']
                base = sym['baseAsset']
                quote = sym['quoteAsset']
                
                # Store pair info
                self.pair_info[pair] = {
                    'base': base,
                    'quote': quote,
                    'pair': pair
                }
                self.tradeable_pairs.add(pair)
            
            print(f"   ✅ {len(self.tradeable_pairs)} pairs loaded")
            
            # UK mode filtering
            if self.binance.uk_mode:
                allowed = self.binance.get_allowed_pairs_uk()
                if allowed:
                    self.tradeable_pairs = self.tradeable_pairs.intersection(allowed)
                    print(f"   🇬🇧 UK Mode: {len(self.tradeable_pairs)} allowed")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    def load_holdings(self):
        """Load account balances"""
        print("\n💰 Loading holdings...")
        
        try:
            account = self.binance.account()
            
            for bal in account.get('balances', []):
                asset = bal['asset']
                free = float(bal.get('free', 0))
                locked = float(bal.get('locked', 0))
                total = free + locked
                
                if total > 0.000001:
                    # Get USD value
                    usd_val = self._get_usd_value(asset, total)
                    
                    if usd_val >= 0.01:
                        self.holdings[asset] = total
                        if usd_val >= 1.0:
                            print(f"   💎 {asset}: {total:.8f} (${usd_val:.2f})")
            
            total_usd = sum(self._get_usd_value(a, b) for a, b in self.holdings.items())
            print(f"\n   💼 Total: ${total_usd:.2f}")
            
            return bool(self.holdings)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def _get_usd_value(self, asset: str, amount: float) -> float:
        """Get USD value"""
        if asset in ['USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'USD']:
            return amount
        
        for quote in ['USDT', 'USDC']:
            pair = f"{asset}{quote}"
            try:
                price = float(self.binance.best_price(pair, timeout=1).get('price', 0))
                if price > 0:
                    return amount * price
            except:
                pass
        
        # Via BTC
        try:
            btc_price = float(self.binance.best_price(f"{asset}BTC", timeout=1).get('price', 0))
            btc_usd = float(self.binance.best_price('BTCUSDT', timeout=1).get('price', 0))
            if btc_price > 0 and btc_usd > 0:
                return amount * btc_price * btc_usd
        except:
            pass
        
        return 0.0
    
    def _get_tradeable_pairs_for_asset(self, asset: str) -> List[Dict]:
        """Get all tradeable pairs for an asset"""
        pairs = []
        
        for pair, info in self.pair_info.items():
            if pair not in self.tradeable_pairs:
                continue
            
            if info['base'] == asset:
                pairs.append({
                    'pair': pair,
                    'side': 'sell',  # Sell base for quote
                    'base': asset,
                    'quote': info['quote']
                })
            elif info['quote'] == asset:
                pairs.append({
                    'pair': pair,
                    'side': 'buy',  # Buy base with quote
                    'base': info['base'],
                    'quote': asset
                })
        
        return pairs
    
    def _get_ws_streams(self) -> List[str]:
        """Get WebSocket streams"""
        streams = set()
        
        for asset in self.holdings.keys():
            for quote in self.QUOTES:
                pair = f"{asset}{quote}"
                if pair in self.tradeable_pairs:
                    streams.add(f"{pair.lower()}@ticker")
                
                inv = f"{quote}{asset}"
                if inv in self.tradeable_pairs:
                    streams.add(f"{inv.lower()}@ticker")
        
        # Add major pairs for reference
        for major in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']:
            if major in self.tradeable_pairs:
                streams.add(f"{major.lower()}@ticker")
        
        return list(streams)[:100]  # Limit
    
    async def run(self):
        """Main loop"""
        print("""
╔══════════════════════════════════════════════════════════════════╗
║   🎯 BINANCE CONVERSION COMMANDO 🎯                              ║
║   Fast spot trading across the Binance ecosystem                 ║
╚══════════════════════════════════════════════════════════════════╝
""")
        
        # Test connection
        print("🔌 Testing connection...")
        if not self.binance.ping():
            print("   ❌ Cannot reach Binance!")
            return
        print("   ✅ Connected!")
        
        self.load_pairs()
        
        if not self.load_holdings():
            print("\n⚠️ No holdings found!")
            return
        
        if self.dry_run:
            print("\n🧪 DRY RUN MODE")
        else:
            print("\n⚠️ Type 'GO' for REAL trading: ", end='')
            if input().strip().upper() != 'GO':
                print("Aborted.")
                return
        
        print("\n🔥 COMMANDO DEPLOYED! 🔥\n")
        
        self.running = True
        self.start_time = datetime.now()
        
        await asyncio.gather(
            self._price_feed(),
            self._trade_loop(),
            self._status_loop(),
        )
        
        self._report()
    
    async def _price_feed(self):
        """WebSocket feed"""
        streams = self._get_ws_streams()
        
        if not streams:
            print("⚠️ No streams!")
            return
        
        url = self.WS_URL + "/".join(streams)
        print(f"📡 Connecting to {len(streams)} feeds...")
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    print(f"   ✅ Connected!")
                    
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            
                            if 'data' in data:
                                t = data['data']
                                symbol = t.get('s', '')
                                price = float(t.get('c', 0))
                                change = float(t.get('P', 0))
                                
                                if price > 0:
                                    now = datetime.now()
                                    
                                    self.current_prices[symbol] = {
                                        'price': price,
                                        'change_24h': change,
                                        'time': now
                                    }
                                    
                                    self.prices[symbol].append((now, price))
                                    
                                    # Keep 3 min history
                                    cutoff = now - timedelta(minutes=3)
                                    self.prices[symbol] = [(t, p) for t, p in self.prices[symbol] if t > cutoff]
                                    
                        except asyncio.TimeoutError:
                            continue
                            
            except Exception as e:
                if self.running:
                    print(f"\n   ⚠️ WS error: {e}")
                    await asyncio.sleep(3)
    
    async def _trade_loop(self):
        """Trading loop"""
        await asyncio.sleep(5)  # Wait for prices
        
        while self.running:
            for asset, balance in list(self.holdings.items()):
                if balance < 0.000001:
                    continue
                
                # Check cooldown
                if asset in self.last_trade:
                    if (datetime.now() - self.last_trade[asset]).seconds < self.cooldown_secs:
                        continue
                
                # Get tradeable pairs
                pairs = self._get_tradeable_pairs_for_asset(asset)
                
                for pair_info in pairs:
                    pair = pair_info['pair']
                    
                    if pair not in self.prices or len(self.prices[pair]) < 5:
                        continue
                    
                    # Calculate momentum
                    history = self.prices[pair]
                    current = history[-1][1]
                    oldest = history[0][1]
                    
                    pct_change = (current - oldest) / oldest * 100
                    
                    # Check threshold (adjusted by snowball)
                    threshold = (self.MIN_MOVE_BPS / 100) / self.snowball
                    
                    if abs(pct_change) >= threshold:
                        await self._execute_trade(asset, pair_info, current, pct_change)
                        break  # One trade per asset per cycle
            
            await asyncio.sleep(1)
    
    async def _execute_trade(self, asset: str, pair_info: Dict, price: float, pct_change: float):
        """Execute a trade"""
        pair = pair_info['pair']
        base = pair_info['base']
        quote = pair_info['quote']
        
        # Determine trade direction based on momentum
        # If price going UP and we hold BASE: SELL (take profit)
        # If price going DOWN and we hold QUOTE: BUY (buy the dip)
        
        if pair_info['side'] == 'sell':
            # We're selling our asset for quote
            if pct_change < 0:
                return  # Don't sell on down momentum
            
            amount = self.holdings[asset]
            usd_val = self._get_usd_value(asset, amount)
            
            if usd_val < self.MIN_VALUE_USD:
                return
            
            # Use portion based on momentum
            trade_pct = min(0.5, 0.2 + abs(pct_change) / 5)
            trade_amount = amount * trade_pct
            trade_val = trade_amount * price
            
            if trade_val < self.MIN_VALUE_USD:
                return
            
            side = 'SELL'
            
        else:
            # We're buying base with our quote asset
            if pct_change > 0:
                return  # Don't buy on up momentum (buy dips)
            
            quote_balance = self.holdings.get(quote, 0)
            usd_val = self._get_usd_value(quote, quote_balance)
            
            if usd_val < self.MIN_VALUE_USD:
                return
            
            trade_pct = min(0.5, 0.2 + abs(pct_change) / 5)
            trade_val = usd_val * trade_pct
            trade_amount = trade_val / price if price > 0 else 0
            
            if trade_val < self.MIN_VALUE_USD:
                return
            
            side = 'BUY'
            asset = quote  # The asset we're spending
        
        print(f"\n   🎯 {side} {pair}: {trade_amount:.8f} @ {price:.8f}")
        print(f"      Movement: {pct_change:+.3f}% | Value: ${trade_val:.2f}")
        
        if self.dry_run:
            print(f"      🧪 DRY RUN")
            self._log_trade(pair, side, trade_amount, trade_val, pct_change, dry_run=True)
            self.last_trade[asset] = datetime.now()
            return
        
        try:
            if side == 'SELL':
                result = self.binance.place_market_order(pair, 'SELL', quantity=trade_amount)
            else:
                result = self.binance.place_market_order(pair, 'BUY', quote_qty=trade_val)
            
            if result.get('rejected'):
                print(f"      ⚠️ Rejected: {result.get('reason')}")
                return
            
            if result.get('status') == 'FILLED' or result.get('orderId'):
                exec_qty = float(result.get('executedQty', trade_amount))
                exec_quote = float(result.get('cummulativeQuoteQty', trade_val))
                
                # Update holdings
                if side == 'SELL':
                    self.holdings[base] = self.holdings.get(base, 0) - exec_qty
                    self.holdings[quote] = self.holdings.get(quote, 0) + exec_quote
                else:
                    self.holdings[base] = self.holdings.get(base, 0) + exec_qty
                    self.holdings[quote] = self.holdings.get(quote, 0) - exec_quote
                
                # Stats
                profit_est = exec_quote * abs(pct_change) / 100
                self.trades += 1
                self.profit += profit_est
                self.snowball *= 1.002  # Grow snowball
                
                self.last_trade[asset] = datetime.now()
                self._log_trade(pair, side, exec_qty, exec_quote, pct_change, profit_est)
                
                print(f"      ✅ FILLED! Profit: ${profit_est:.4f}")
            else:
                print(f"      ⚠️ Unknown result: {result}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    def _log_trade(self, pair: str, side: str, qty: float, value: float, 
                   momentum: float, profit: float = 0, dry_run: bool = False):
        """Log trade"""
        self.trade_log.append({
            'time': datetime.now().isoformat(),
            'pair': pair,
            'side': side,
            'qty': qty,
            'value': value,
            'momentum': momentum,
            'profit': profit,
            'dry_run': dry_run
        })
    
    async def _status_loop(self):
        """Status display"""
        while self.running:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            hours = max(0.001, elapsed / 3600)
            velocity = self.profit / hours
            
            # Top movers
            movers = []
            for pair, hist in self.prices.items():
                if len(hist) < 2:
                    continue
                pct = (hist[-1][1] - hist[0][1]) / hist[0][1] * 100
                movers.append((pair, pct))
            
            movers.sort(key=lambda x: abs(x[1]), reverse=True)
            top = movers[:3]
            
            mover_str = " | ".join([f"{p}:{c:+.2f}%" for p, c in top]) if top else "..."
            
            print(f"\r⏱️ {int(elapsed)}s | 🎯 {self.trades} | "
                  f"💰 ${self.profit:.4f} | ⚡${velocity:.2f}/hr | "
                  f"❄️ {self.snowball:.3f}x | {mover_str}",
                  end='', flush=True)
            
            await asyncio.sleep(5)
    
    def _report(self):
        """Final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print("\n\n" + "="*60)
        print("📊 COMMANDO SESSION REPORT")
        print("="*60)
        print(f"⏱️ Runtime: {elapsed:.0f}s")
        print(f"🎯 Trades: {self.trades}")
        print(f"💰 Profit: ${self.profit:.4f}")
        print(f"❄️ Snowball: {self.snowball:.4f}x")
        
        if self.trade_log:
            print("\n📝 Trade Log (last 20):")
            for t in self.trade_log[-20:]:
                tag = "🧪" if t.get('dry_run') else "✅"
                print(f"   {tag} {t['side']} {t['pair']}: {t['qty']:.8f} ({t['momentum']:+.2f}%)")
        
        print("="*60)


async def main():
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    commando = BinanceConversionCommando(dry_run=dry_run)
    await commando.run()


if __name__ == "__main__":
    asyncio.run(main())
