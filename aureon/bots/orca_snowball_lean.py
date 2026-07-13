#!/usr/bin/env python3
"""
🏔️❄️ ORCA SNOWBALL - ARBITRAGE STYLE ❄️🏔️

Fast, lean, direct trading like the arbitrage system.
Scans → Finds opportunity → Executes IMMEDIATELY.

NO HEAVY IMPORTS. NO SLOW INIT. JUST FIRE.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# === CONSTANTS ===
MILLION = 1_000_000
MIN_SPREAD = 0.10  # 0.1% minimum spread for arbitrage
MIN_MOMENTUM = 5.0  # 5% minimum change for momentum

def log(prefix: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {prefix} {msg}")

def log_snow(msg): log("❄️", msg)
def log_fire(msg): log("🔥", msg)
def log_win(msg): log("💰", msg)
def log_queen(msg): log("👑", msg)

class OrcaSnowballLean:
    """Lean snowball - arbitrage style"""
    
    def __init__(self, clients: Optional[Dict] = None):
        log_snow("Initializing Lean Snowball...")
        
        # Direct API setup - no heavy imports
        self.kraken_key = os.environ.get('KRAKEN_API_KEY', '')
        self.kraken_secret = os.environ.get('KRAKEN_API_SECRET', '')
        self.binance_key = os.environ.get('BINANCE_API_KEY', '')
        self.binance_secret = os.environ.get('BINANCE_API_SECRET', '')
        
        # Lazy load clients only when needed
        self._kraken = clients.get('kraken') if clients else None
        self._binance = clients.get('binance') if clients else None
        
        self.trades_executed = 0
        self.total_profit = 0
        
        log_snow("Ready to hunt!")
        
    @property
    def kraken(self):
        if self._kraken is None:
            from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
            self._kraken = get_kraken_client()
        return self._kraken
        
    @property  
    def binance(self):
        if self._binance is None:
            from aureon.exchanges.binance_client import BinanceClient, get_binance_client
            self._binance = get_binance_client()
        return self._binance
        
    def get_portfolio_value(self) -> float:
        """Quick portfolio check"""
        total = 0
        
        # Kraken
        try:
            bal = self.kraken.get_balance()
            usd = float(bal.get('USD', 0)) + float(bal.get('ZUSD', 0))
            total += usd
            
            # SOL value
            sol = float(bal.get('SOL', 0))
            if sol > 0:
                ticker = self.kraken.get_ticker('SOLUSD')
                total += sol * float(ticker.get('price', 0))
        except:
            pass
            
        # Binance
        try:
            bal = self.binance.get_balance()
            usdt = float(bal.get('USDT', 0)) + float(bal.get('USDC', 0))
            total += usdt
        except:
            pass
            
        return total
        
    def scan_arbitrage(self) -> List[Dict]:
        """Fast arbitrage scan using public APIs"""
        opportunities = []
        
        pairs = [
            ('BTC', 'XBTUSD', 'BTCUSDT'),
            ('ETH', 'ETHUSD', 'ETHUSDT'),
            ('SOL', 'SOLUSD', 'SOLUSDT'),
            ('XRP', 'XRPUSD', 'XRPUSDT'),
            ('DOGE', 'DOGEUSD', 'DOGEUSDT'),
            ('ADA', 'ADAUSD', 'ADAUSDT'),
        ]
        
        try:
            # Kraken public API
            k_params = ','.join([p[1] for p in pairs])
            k_resp = requests.get(
                'https://api.kraken.com/0/public/Ticker',
                params={'pair': k_params},
                timeout=5
            )
            k_data = k_resp.json().get('result', {})
            
            kraken_prices = {}
            for pair, data in k_data.items():
                price = float(data['c'][0])
                # Map to coin name
                for coin, k_pair, _ in pairs:
                    if k_pair.replace('USD', '') in pair or coin in pair:
                        kraken_prices[coin] = price
                        break
                        
            # Binance public API
            b_resp = requests.get('https://api.binance.com/api/v3/ticker/price', timeout=5)
            b_data = {t['symbol']: float(t['price']) for t in b_resp.json()}
            
            binance_prices = {}
            for coin, _, b_pair in pairs:
                if b_pair in b_data:
                    binance_prices[coin] = b_data[b_pair]
                    
            # Find spreads
            for coin, k_pair, b_pair in pairs:
                k_price = kraken_prices.get(coin, 0)
                b_price = binance_prices.get(coin, 0)
                
                if k_price > 0 and b_price > 0:
                    spread_pct = abs(k_price - b_price) / min(k_price, b_price) * 100
                    
                    if spread_pct >= MIN_SPREAD:
                        buy_ex = 'kraken' if k_price < b_price else 'binance'
                        sell_ex = 'binance' if k_price < b_price else 'kraken'
                        
                        opportunities.append({
                            'type': 'ARBITRAGE',
                            'coin': coin,
                            'kraken_pair': k_pair,
                            'binance_pair': b_pair,
                            'kraken_price': k_price,
                            'binance_price': b_price,
                            'spread_pct': spread_pct,
                            'buy_exchange': buy_ex,
                            'sell_exchange': sell_ex,
                            'score': 10 + spread_pct,  # Higher spread = higher score
                        })
                        
        except Exception as e:
            log_fire(f"Arbitrage scan error: {e}")
            
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def scan_momentum(self) -> List[Dict]:
        """Scan Binance for momentum"""
        opportunities = []
        
        try:
            resp = requests.get(
                'https://api.binance.com/api/v3/ticker/24hr',
                timeout=10
            )
            
            for ticker in resp.json():
                symbol = ticker.get('symbol', '')
                if not symbol.endswith('USDT'):
                    continue
                    
                change = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('quoteVolume', 0))
                price = float(ticker.get('lastPrice', 0))
                
                # Strong uptrend with volume
                if MIN_MOMENTUM < change < 50 and volume > 500000 and price > 0:
                    opportunities.append({
                        'type': 'MOMENTUM',
                        'symbol': symbol,
                        'coin': symbol.replace('USDT', ''),
                        'price': price,
                        'change_24h': change,
                        'volume': volume,
                        'exchange': 'binance',
                        'score': change / 5,  # Scale score
                    })
                    
        except Exception as e:
            log_fire(f"Momentum scan error: {e}")
            
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)[:10]
        
    def scan_kraken_dips(self) -> List[Dict]:
        """Scan Kraken for dip buys"""
        opportunities = []
        
        pairs = ['SOLUSD', 'ETHUSD', 'XRPUSD', 'ADAUSD', 'DOGEUSD']
        
        try:
            resp = requests.get(
                'https://api.kraken.com/0/public/Ticker',
                params={'pair': ','.join(pairs)},
                timeout=5
            )
            data = resp.json().get('result', {})
            
            for pair, ticker in data.items():
                price = float(ticker['c'][0])
                high = float(ticker['h'][1])  # 24h high
                low = float(ticker['l'][1])   # 24h low
                
                if high > low:
                    # Position in range (0 = at low, 100 = at high)
                    position = (price - low) / (high - low) * 100
                    range_pct = (high - low) / low * 100
                    
                    # Good buy if in lower 25% of range with decent volatility
                    if position < 25 and range_pct > 2:
                        coin = pair.replace('USD', '').replace('X', '').replace('Z', '')
                        opportunities.append({
                            'type': 'DIP_BUY',
                            'symbol': pair,
                            'coin': coin,
                            'price': price,
                            'high_24h': high,
                            'low_24h': low,
                            'position_pct': position,
                            'range_pct': range_pct,
                            'exchange': 'kraken',
                            'score': (25 - position) / 5 + range_pct / 2,
                        })
                        
        except Exception as e:
            log_fire(f"Dip scan error: {e}")
            
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def execute_arbitrage(self, opp: Dict) -> bool:
        """Execute arbitrage trade"""
        coin = opp['coin']
        buy_ex = opp['buy_exchange']
        sell_ex = opp['sell_exchange']
        spread = opp['spread_pct']
        
        log_fire(f"⚡ ARBITRAGE: {coin}")
        log_fire(f"   BUY on {buy_ex} @ ${opp['kraken_price' if buy_ex == 'kraken' else 'binance_price']:.2f}")
        log_fire(f"   SELL on {sell_ex} @ ${opp['binance_price' if sell_ex == 'binance' else 'kraken_price']:.2f}")
        log_fire(f"   Spread: {spread:.3f}%")
        
        # Get available funds on buy exchange
        if buy_ex == 'kraken':
            try:
                bal = self.kraken.get_balance()
                usd = float(bal.get('USD', 0))
                
                if usd < 10:
                    log_fire(f"   ⚠️ Insufficient USD: ${usd:.2f}")
                    return False
                    
                # Use 50% of available
                trade_usd = usd * 0.5
                buy_price = opp['kraken_price']
                volume = trade_usd / buy_price
                
                # Round appropriately
                if buy_price > 1000:
                    volume = round(volume, 5)
                else:
                    volume = round(volume, 3)
                    
                log_fire(f"   📊 Buying {volume} {coin} for ${trade_usd:.2f}")
                
                # Execute buy
                result = self.kraken.place_market_order(opp['kraken_pair'], 'buy', volume)
                
                if result and result.get('status') == 'FILLED':
                    log_win(f"💥 BOUGHT {volume} {coin} @ ${buy_price:.2f}")
                    self.trades_executed += 1
                    
                    # Save trade
                    self._log_trade('BUY', coin, buy_ex, volume, buy_price)
                    return True
                else:
                    log_fire(f"   ❌ Buy failed: {result}")
                    
            except Exception as e:
                log_fire(f"   ❌ Kraken error: {e}")
                
        elif buy_ex == 'binance':
            try:
                bal = self.binance.get_balance()
                usdt = float(bal.get('USDT', 0))
                
                if usdt < 10:
                    log_fire(f"   ⚠️ Insufficient USDT: ${usdt:.2f}")
                    return False
                    
                trade_usd = usdt * 0.5
                buy_price = opp['binance_price']
                volume = trade_usd / buy_price
                
                # Adjust for Binance lot size
                volume = self.binance.adjust_quantity(opp['binance_pair'], volume)
                
                log_fire(f"   📊 Buying {volume} {coin} for ${trade_usd:.2f}")
                
                result = self.binance.place_market_order(opp['binance_pair'], 'BUY', volume)
                
                if result and result.get('status') == 'FILLED':
                    log_win(f"💥 BOUGHT {volume} {coin} @ ${buy_price:.6f}")
                    self.trades_executed += 1
                    self._log_trade('BUY', coin, buy_ex, volume, buy_price)
                    return True
                else:
                    log_fire(f"   ❌ Buy failed: {result}")
                    
            except Exception as e:
                log_fire(f"   ❌ Binance error: {e}")
                
        return False
        
    def execute_momentum(self, opp: Dict) -> bool:
        """Execute momentum trade on Binance"""
        symbol = opp['symbol']
        price = opp['price']
        change = opp['change_24h']
        
        log_fire(f"⚡ MOMENTUM: {symbol}")
        log_fire(f"   Price: ${price:.6f} | Change: {change:+.1f}%")
        
        try:
            # Check if tradeable
            if not self.binance.can_trade_symbol(symbol):
                log_fire(f"   ⚠️ UK restricted: {symbol}")
                return False
                
            bal = self.binance.get_balance()
            usdt = float(bal.get('USDT', 0)) + float(bal.get('USDC', 0))
            
            if usdt < 5:
                log_fire(f"   ⚠️ Insufficient USDT: ${usdt:.2f}")
                return False
                
            trade_usd = min(usdt * 0.3, 20)  # Max $20 per momentum trade
            volume = self.binance.adjust_quantity(symbol, trade_usd / price)
            
            log_fire(f"   📊 Buying {volume} for ${trade_usd:.2f}")
            
            result = self.binance.place_market_order(symbol, 'BUY', volume)
            
            if result and result.get('status') == 'FILLED':
                log_win(f"💥 BOUGHT {symbol} @ ${price:.6f}")
                self.trades_executed += 1
                self._log_trade('BUY', symbol, 'binance', volume, price)
                return True
            else:
                log_fire(f"   ❌ Failed: {result}")
                
        except Exception as e:
            log_fire(f"   ❌ Error: {e}")
            
        return False
        
    def execute_dip(self, opp: Dict) -> bool:
        """Execute dip buy on Kraken"""
        symbol = opp['symbol']
        price = opp['price']
        position = opp['position_pct']
        
        log_fire(f"⚡ DIP BUY: {symbol}")
        log_fire(f"   Price: ${price:.2f} | Position in range: {position:.0f}%")
        
        try:
            bal = self.kraken.get_balance()
            usd = float(bal.get('USD', 0))
            
            if usd < 10:
                log_fire(f"   ⚠️ Insufficient USD: ${usd:.2f}")
                return False
                
            trade_usd = usd * 0.5
            volume = trade_usd / price
            
            if price > 100:
                volume = round(volume, 4)
            else:
                volume = round(volume, 2)
                
            log_fire(f"   📊 Buying {volume} for ${trade_usd:.2f}")
            
            result = self.kraken.place_market_order(symbol, 'buy', volume)
            
            if result and result.get('status') == 'FILLED':
                log_win(f"💥 BOUGHT {volume} @ ${price:.2f}")
                self.trades_executed += 1
                self._log_trade('BUY', symbol, 'kraken', volume, price)
                return True
            else:
                log_fire(f"   ❌ Failed: {result}")
                
        except Exception as e:
            log_fire(f"   ❌ Error: {e}")
            
        return False
        
    def check_profit_targets(self):
        """Check positions for profit-taking"""
        log_snow("🔍 Checking profit targets...")
        
        # Check Kraken positions
        try:
            bal = self.kraken.get_balance()
            
            for asset, qty in bal.items():
                qty = float(qty)
                if qty <= 0 or asset in ['USD', 'ZUSD', 'ZGBP', 'TUSD', 'ZEUR']:
                    continue
                    
                pair = f"{asset}USD"
                try:
                    ticker = self.kraken.get_ticker(pair)
                    if not ticker:
                        continue
                        
                    price = float(ticker.get('price', 0))
                    value = qty * price
                    
                    if value < 5:
                        continue
                        
                    high = float(ticker.get('high', price))
                    low = float(ticker.get('low', price))
                    
                    if high > low:
                        position = (price - low) / (high - low) * 100
                        
                        # Take profit if in top 20% of range
                        if position > 80:
                            log_snow(f"   📈 {asset}: ${value:.2f} at {position:.0f}% of range - TAKING PROFIT")
                            
                            sell_qty = qty * 0.5  # Sell half
                            result = self.kraken.place_market_order(pair, 'sell', sell_qty)
                            
                            if result and result.get('status') == 'FILLED':
                                received = float(result.get('receivedQty', 0))
                                log_win(f"💰 SOLD {sell_qty:.4f} {asset} → ${received:.2f}")
                                self.trades_executed += 1
                                self.total_profit += received
                                self._log_trade('SELL', asset, 'kraken', sell_qty, price)
                                
                except:
                    pass
                    
        except Exception as e:
            log_fire(f"Profit check error: {e}")
            
    def _log_trade(self, side: str, symbol: str, exchange: str, qty: float, price: float):
        """Log trade to file"""
        try:
            trade = {
                'timestamp': datetime.now().isoformat(),
                'side': side,
                'symbol': symbol,
                'exchange': exchange,
                'qty': qty,
                'price': price,
                'value': qty * price
            }
            with open('snowball_trades.json', 'a') as f:
                f.write(json.dumps(trade) + '\n')
        except:
            pass
            
    def run_cycle(self):
        """Run one snowball cycle"""
        print()
        log_snow("=" * 50)
        log_snow("   SNOWBALL CYCLE")
        log_snow("=" * 50)
        
        # Portfolio check
        portfolio = self.get_portfolio_value()
        progress = (portfolio / MILLION) * 100
        doublings = 0
        temp = portfolio
        while temp < MILLION:
            temp *= 2
            doublings += 1
            
        log_snow(f"💰 Portfolio: ${portfolio:.2f}")
        log_snow(f"🎯 Target: ${MILLION:,}")
        log_snow(f"📊 Progress: {progress:.6f}%")
        log_snow(f"🔄 Doublings needed: {doublings}")
        
        if portfolio >= MILLION:
            log_win("🏆🏆🏆 MILLION REACHED! 🏆🏆🏆")
            return True
            
        # Check profit targets first
        self.check_profit_targets()
        
        # Scan for opportunities
        log_snow("\n🔍 Scanning markets...")
        
        arb_opps = self.scan_arbitrage()
        mom_opps = self.scan_momentum()
        dip_opps = self.scan_kraken_dips()
        
        log_snow(f"   Arbitrage: {len(arb_opps)}")
        log_snow(f"   Momentum: {len(mom_opps)}")
        log_snow(f"   Dip buys: {len(dip_opps)}")
        
        # Display top opportunities
        print()
        log_queen("👑 TOP OPPORTUNITIES:")
        
        for opp in arb_opps[:3]:
            log_queen(f"   💱 ARBITRAGE {opp['coin']}: {opp['spread_pct']:.3f}% spread")
            
        for opp in mom_opps[:3]:
            log_queen(f"   🚀 MOMENTUM {opp['symbol']}: {opp['change_24h']:+.1f}%")
            
        for opp in dip_opps[:3]:
            log_queen(f"   📉 DIP {opp['symbol']}: {opp['position_pct']:.0f}% in range")
            
        # Execute best opportunity
        executed = False
        
        # Priority 1: Arbitrage (highest score = most profit potential)
        if arb_opps and arb_opps[0]['score'] >= 10:
            log_queen(f"\n👑 EXECUTING ARBITRAGE: {arb_opps[0]['coin']}")
            executed = self.execute_arbitrage(arb_opps[0])
            
        # Priority 2: Strong momentum
        if not executed and mom_opps and mom_opps[0]['score'] >= 4:
            log_queen(f"\n👑 EXECUTING MOMENTUM: {mom_opps[0]['symbol']}")
            executed = self.execute_momentum(mom_opps[0])
            
        # Priority 3: Dip buys
        if not executed and dip_opps and dip_opps[0]['score'] >= 3:
            log_queen(f"\n👑 EXECUTING DIP BUY: {dip_opps[0]['symbol']}")
            executed = self.execute_dip(dip_opps[0])
            
        if not executed:
            log_queen("\n👑 No opportunities above threshold. Waiting...")
            
        log_snow(f"\n📊 Session: {self.trades_executed} trades, ${self.total_profit:.2f} profit")
        
        return False
        
    def run_forever(self, cycle_seconds: int = 30):
        """Run until million"""
        print()
        print("🏔️" + "❄️" * 25 + "🏔️")
        print("   ORCA SNOWBALL TO MILLION")
        print("   Arbitrage Style - Fast & Lean")
        print("🏔️" + "❄️" * 25 + "🏔️")
        print()
        
        while True:
            try:
                reached = self.run_cycle()
                if reached:
                    break
            except KeyboardInterrupt:
                log_snow("\n⏸️ Stopped by user")
                break
            except Exception as e:
                log_fire(f"Cycle error: {e}")
                
            log_snow(f"\n⏳ Next cycle in {cycle_seconds}s...")
            time.sleep(cycle_seconds)
            

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle', type=int, default=30)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    
    snowball = OrcaSnowballLean()
    
    if args.once:
        snowball.run_cycle()
    else:
        snowball.run_forever(args.cycle)
        

if __name__ == '__main__':
    main()
