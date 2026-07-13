#!/usr/bin/env python3
"""
🔥⚡ GAIA AGGRESSIVE RECLAIMER ⚡🔥
NO GATES. NO WAITING. JUST TAKE.

Based on the WORKING rotations from this chat:
- Buy SOL → Wait → Sell SOL → Buy BTC → Wait → Sell BTC → Repeat
- Any profit = TAKE IT
- Deploy ALL cash immediately
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
os.environ['PYTHONUNBUFFERED'] = '1'

import time
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.getcwd())

# Sacred Constants
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN = 7.83

class AggressiveReclaimer:
    def __init__(self):
        print("🔥" * 40)
        print("   GAIA AGGRESSIVE RECLAIMER - TAKE EVERYTHING")
        print("🔥" * 40)
        
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        from aureon.exchanges.alpaca_client import AlpacaClient
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        
        self.binance = get_binance_client()
        self.alpaca = AlpacaClient()
        self.kraken = get_kraken_client()
        
        self.trades = 0
        self.profit = 0.0
        self.net_profit = 0.0
        
        # Track our entry prices PER ASSET
        self.entries = {}

        # Alpaca cost model (percentages)
        self.alpaca_fee_pct = float(os.getenv("ALPACA_FEE_PCT", "0.25"))
        self.alpaca_slippage_pct = float(os.getenv("ALPACA_SLIPPAGE_PCT", "0.02"))
        self.alpaca_fee_buffer_pct = float(os.getenv("ALPACA_FEE_BUFFER_PCT", "0.01"))
        self.alpaca_min_net_profit_pct = float(os.getenv("ALPACA_MIN_NET_PROFIT_PCT", "0.01"))
        
        print("✅ BINANCE | ALPACA | KRAKEN - ALL CONNECTED")
        print()
        
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def _alpaca_format_symbol(self, symbol: str) -> str:
        if not symbol:
            return symbol
        if "/" in symbol:
            return symbol
        if symbol.endswith("USD"):
            return f"{symbol[:-3]}/USD"
        if symbol.endswith("USDC"):
            return f"{symbol[:-4]}/USDC"
        return symbol

    def _alpaca_get_spread_pct(self, symbol: str) -> float:
        try:
            alpaca_symbol = self._alpaca_format_symbol(symbol)
            quotes = self.alpaca.get_latest_crypto_quotes([alpaca_symbol])
            quote = quotes.get(alpaca_symbol, {}) or quotes.get(symbol, {}) or {}
            bid = float(quote.get("bp", 0) or 0)
            ask = float(quote.get("ap", 0) or 0)
            mid = (bid + ask) / 2 if bid and ask else 0
            if mid <= 0:
                return 0.0
            return ((ask - bid) / mid) * 100
        except Exception:
            return 0.0

    def _alpaca_estimate_exit_costs(self, symbol: str) -> dict:
        spread_pct = self._alpaca_get_spread_pct(symbol)
        fee_pct = self.alpaca_fee_pct
        total_pct = fee_pct + self.alpaca_slippage_pct + spread_pct + self.alpaca_fee_buffer_pct
        return {
            "fee_pct": fee_pct,
            "slippage_pct": self.alpaca_slippage_pct,
            "spread_pct": spread_pct,
            "fee_buffer_pct": self.alpaca_fee_buffer_pct,
            "total_pct": total_pct,
        }

    # ═══════════════════════════════════════════════════════════════
    # BINANCE - FAST EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def binance_scan_and_trade(self):
        """Scan Binance positions - take any profit - deploy all cash"""
        try:
            # Check what we hold
            for asset in ['SOL', 'BTC', 'ETH', 'AVAX', 'DOGE', 'XRP']:
                bal = self.binance.get_free_balance(asset)
                if bal < 0.00001:
                    continue
                
                pair = f'{asset}USDC'
                t = self.binance.get_ticker_price(pair)
                if not t:
                    continue
                    
                price = float(t.get('price', 0))
                value = bal * price
                
                if value < 1:
                    continue
                
                # Get entry - if none, set it NOW
                key = f'bin_{asset}'
                if key not in self.entries:
                    self.entries[key] = price
                    self.log(f"📍 BINANCE {asset}: Entry set @ ${price:.4f}")
                    continue
                
                entry = self.entries[key]
                pnl_pct = (price - entry) / entry * 100
                
                # ANY PROFIT = SELL
                if pnl_pct > 0.01:  # Just 0.01% profit threshold
                    self.log(f"🔥 BINANCE SELL {asset}: ${value:.2f} ({pnl_pct:+.2f}%)")
                    
                    result = self.binance.place_market_order(pair, 'SELL', quantity=bal * 0.999)
                    
                    if result and ('orderId' in result or result.get('status') == 'FILLED'):
                        profit_usd = value * (pnl_pct / 100)
                        self.profit += profit_usd
                        self.trades += 1
                        self.log(f"   ✅ SOLD! +${profit_usd:.4f}")
                        
                        # Remove entry so we reset on next buy
                        del self.entries[key]
                        
                        time.sleep(0.3)
                        
                        # Immediately buy next best
                        self._binance_buy_best()
                    else:
                        self.log(f"   ⚠️ Sell failed: {result}")
                        
            # Deploy any idle USDC
            usdc = self.binance.get_free_balance('USDC')
            if usdc > 2:
                self._binance_buy_best()
                
        except Exception as e:
            self.log(f"⚠️ Binance error: {e}")
    
    def _binance_buy_best(self):
        """Buy the best momentum asset on Binance"""
        usdc = self.binance.get_free_balance('USDC')
        if usdc < 2:
            return
            
        # Find best momentum
        pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC', 'AVAXUSDC', 'DOGEUSDC']
        best_pair, best_mom = None, -999
        
        for pair in pairs:
            try:
                t = self.binance.get_24h_ticker(pair)
                mom = float(t.get('priceChangePercent', 0))
                if mom > best_mom:
                    best_pair, best_mom = pair, mom
            except:
                pass
        
        if best_pair:
            asset = best_pair.replace('USDC', '')
            self.log(f"📥 BINANCE BUY {asset}: ${usdc:.2f} ({best_mom:+.1f}%)")
            
            result = self.binance.place_market_order(best_pair, 'BUY', quote_qty=usdc * 0.98)
            
            if result and ('orderId' in result or result.get('status') == 'FILLED'):
                # Record entry price
                t = self.binance.get_ticker_price(best_pair)
                price = float(t.get('price', 0))
                self.entries[f'bin_{asset}'] = price
                self.log(f"   ✅ BOUGHT @ ${price:.4f}")
            else:
                self.log(f"   ⚠️ Buy failed: {result}")

    # ═══════════════════════════════════════════════════════════════
    # ALPACA - FAST EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def alpaca_scan_and_trade(self):
        """Scan Alpaca - take profits - deploy cash"""
        try:
            positions = self.alpaca.get_positions()
            
            for pos in positions:
                sym = pos.get('symbol', '')
                qty = float(pos.get('qty', 0))
                entry = float(pos.get('avg_entry_price', 0))
                current = float(pos.get('current_price', 0))
                value = float(pos.get('market_value', 0))
                
                if value < 0.5:
                    continue
                
                pnl_pct = (current - entry) / entry * 100 if entry > 0 else 0
                cost_metrics = self._alpaca_estimate_exit_costs(sym)
                net_pnl_pct = pnl_pct - cost_metrics["total_pct"]
                
                # Only sell if NET profit clears fees/slippage/spread
                if net_pnl_pct > self.alpaca_min_net_profit_pct:
                    asset = sym.replace('USD', '').replace('/', '')
                    self.log(
                        f"🔥 ALPACA SELL {asset}: ${value:.2f} "
                        f"(gross {pnl_pct:+.2f}%, net {net_pnl_pct:+.2f}%, "
                        f"fees {cost_metrics['total_pct']:.2f}%)"
                    )
                    
                    result = self.alpaca.place_order(sym, qty, 'sell', 'market', 'ioc')
                    
                    if result and result.get('status') in ['filled', 'accepted', 'new']:
                        profit_usd = value * (pnl_pct / 100)
                        net_profit_usd = value * (net_pnl_pct / 100)
                        self.profit += profit_usd
                        self.net_profit += net_profit_usd
                        self.trades += 1
                        self.log(f"   ✅ SOLD! +${net_profit_usd:.4f} net (${profit_usd:.4f} gross)")
                        
                        time.sleep(0.5)
                        self._alpaca_buy_best()
                    else:
                        self.log(f"   ⚠️ Sell failed: {result}")
                else:
                    self.log(
                        f"⏸️ ALPACA HOLD {sym}: gross {pnl_pct:+.2f}% "
                        f"< fees {cost_metrics['total_pct']:.2f}% (net {net_pnl_pct:+.2f}%)"
                    )
            
            # Deploy cash
            acc = self.alpaca.get_account()
            cash = float(acc.get('cash', 0))
            if cash > 2:
                self._alpaca_buy_best()
                
        except Exception as e:
            self.log(f"⚠️ Alpaca error: {e}")
    
    def _alpaca_buy_best(self):
        """Buy best on Alpaca"""
        try:
            acc = self.alpaca.get_account()
            cash = float(acc.get('cash', 0))
            if cash < 2:
                return
            
            # Use Binance momentum data
            pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC']
            best_asset, best_mom = None, -999
            
            for pair in pairs:
                try:
                    t = self.binance.get_24h_ticker(pair)
                    mom = float(t.get('priceChangePercent', 0))
                    if mom > best_mom:
                        best_asset = pair.replace('USDC', '')
                        best_mom = mom
                except:
                    pass
            
            if best_asset:
                alpaca_sym = f'{best_asset}/USD'
                self.log(f"📥 ALPACA BUY {best_asset}: ${cash:.2f} ({best_mom:+.1f}%)")
                
                # Get price and calc qty
                try:
                    quotes = self.alpaca.get_latest_crypto_quotes([alpaca_sym])
                    price = float(quotes[alpaca_sym].get('ap', 0))
                    qty = (cash * 0.95) / price
                    
                    result = self.alpaca.place_order(alpaca_sym, qty, 'buy', 'market', 'ioc')
                    if result:
                        self.log(f"   ✅ BOUGHT")
                except Exception as e:
                    self.log(f"   ⚠️ Buy error: {e}")
                    
        except Exception as e:
            self.log(f"⚠️ Alpaca buy error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # KRAKEN - FAST EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def kraken_scan_and_trade(self):
        """Scan Kraken - take profits - deploy USD"""
        try:
            acct = self.kraken.account()
            usd_bal = 0
            
            for bal in acct.get('balances', []):
                asset = bal.get('asset', '')
                free = float(bal.get('free', 0))
                
                if free <= 0:
                    continue
                
                # Track USD
                if asset in ['USD', 'USDC', 'ZUSD']:
                    usd_bal += free
                    continue
                
                if asset in ['USDT', 'EUR', 'ZEUR']:
                    continue
                
                # It's a crypto - check value
                pair = f'{asset}USD'
                try:
                    ticker = self.kraken.get_ticker(pair)
                    price = float(ticker.get('price', 0))
                except:
                    continue
                
                value = free * price
                if value < 1:
                    continue
                
                # Get entry
                key = f'krk_{asset}'
                if key not in self.entries:
                    self.entries[key] = price
                    self.log(f"📍 KRAKEN {asset}: Entry set @ ${price:.4f}")
                    continue
                
                entry = self.entries[key]
                pnl_pct = (price - entry) / entry * 100
                
                # ANY PROFIT = SELL
                if pnl_pct > 0.01:
                    self.log(f"🔥 KRAKEN SELL {asset}: ${value:.2f} ({pnl_pct:+.2f}%)")
                    
                    result = self.kraken.place_market_order(pair, 'sell', quantity=free * 0.999)
                    
                    # Check for ANY success indicator
                    if result and (result.get('txid') or result.get('status') == 'FILLED' or 
                                   result.get('orderId') or 'dryRun' in result):
                        profit_usd = value * (pnl_pct / 100)
                        self.profit += profit_usd
                        self.trades += 1
                        self.log(f"   ✅ SOLD! +${profit_usd:.4f}")
                        
                        del self.entries[key]
                        time.sleep(0.3)
                        self._kraken_buy_best()
                    else:
                        self.log(f"   ⚠️ Sell failed: {result}")
            
            # Deploy USD
            if usd_bal > 2:
                self._kraken_buy_best()
                
        except Exception as e:
            self.log(f"⚠️ Kraken error: {e}")
    
    def _kraken_buy_best(self):
        """Buy best on Kraken"""
        try:
            acct = self.kraken.account()
            usd = sum(float(b.get('free', 0)) for b in acct.get('balances', []) 
                     if b.get('asset') in ['USD', 'USDC', 'ZUSD'])
            
            if usd < 2:
                return
            
            # Use Binance momentum
            pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC']
            best_asset, best_mom = None, -999
            
            for pair in pairs:
                try:
                    t = self.binance.get_24h_ticker(pair)
                    mom = float(t.get('priceChangePercent', 0))
                    if mom > best_mom:
                        best_asset = pair.replace('USDC', '')
                        best_mom = mom
                except:
                    pass
            
            if best_asset:
                kraken_pair = f'{best_asset}USD'
                self.log(f"📥 KRAKEN BUY {best_asset}: ${usd:.2f} ({best_mom:+.1f}%)")
                
                result = self.kraken.place_market_order(kraken_pair, 'buy', quote_qty=usd * 0.95)
                
                if result and (result.get('txid') or 'dryRun' in result):
                    ticker = self.kraken.get_ticker(kraken_pair)
                    price = float(ticker.get('price', 0))
                    self.entries[f'krk_{best_asset}'] = price
                    self.log(f"   ✅ BOUGHT @ ${price:.4f}")
                else:
                    self.log(f"   ⚠️ Buy failed: {result}")
                    
        except Exception as e:
            self.log(f"⚠️ Kraken buy error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # MAIN LOOP - PARALLEL AGGRESSIVE SCANNING
    # ═══════════════════════════════════════════════════════════════
    
    def run_cycle(self):
        """Run one aggressive cycle across all platforms"""
        with ThreadPoolExecutor(max_workers=3) as ex:
            ex.submit(self.binance_scan_and_trade)
            ex.submit(self.alpaca_scan_and_trade)
            ex.submit(self.kraken_scan_and_trade)
    
    def print_status(self):
        """Quick status"""
        self.log(
            f"═══ TRADES: {self.trades} | GROSS: ${self.profit:.4f} | "
            f"NET: ${self.net_profit:.4f} | ENTRIES: {len(self.entries)} ═══"
        )
    
    def run(self):
        """RUN FOREVER - TAKE EVERYTHING"""
        print()
        print("⚡ AGGRESSIVE MODE: 0.01% profit threshold")
        print("⚡ NO GATES - Just profits")
        print("⚡ Parallel scanning all 3 platforms")
        print()
        
        cycle = 0
        while True:
            try:
                self.run_cycle()
                cycle += 1
                
                if cycle % 5 == 0:
                    self.print_status()
                
                time.sleep(1)  # Fast cycle
                
            except KeyboardInterrupt:
                print()
                self.log("🛑 STOPPED")
                self.print_status()
                break
            except Exception as e:
                self.log(f"ERROR: {e}")
                time.sleep(2)


if __name__ == "__main__":
    r = AggressiveReclaimer()
    r.run()
