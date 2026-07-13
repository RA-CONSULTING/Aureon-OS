#!/usr/bin/env python3
"""
🔥⚡ GAIA TURBO TRADER - ALL PLATFORMS, ALL ASSETS, NON-STOP ⚡🔥
Takes profits across ALL exchanges simultaneously.
Optimized for speed with parallel network calls.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
os.environ['PYTHONUNBUFFERED'] = '1'

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Adjust path to find modules
sys.path.append(os.getcwd())

@dataclass
class Position:
    asset: str
    platform: str
    qty: float
    entry_price: float
    current_price: float = 0
    
    @property
    def value(self) -> float:
        return self.qty * self.current_price
    
    @property
    def pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0
        return (self.current_price - self.entry_price) / self.entry_price * 100

class GaiaTurboTrader:
    def __init__(self):
        self.trades_taken = 0
        self.total_profit = 0.0
        self.min_profit_pct = 0.05  # Take at 0.05% profit
        self.entries: Dict[str, float] = {}
        self.lock = threading.Lock()
        
        # Connect to exchanges
        print("🔌 Connecting to ALL platforms...")
        
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        from aureon.exchanges.alpaca_client import AlpacaClient
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        
        self.binance = get_binance_client()
        self.alpaca = AlpacaClient()
        self.kraken = get_kraken_client()
        
        print("✅ BINANCE connected")
        print("✅ ALPACA connected")
        print("✅ KRAKEN connected")
        print()
        
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def get_binance_data(self) -> Tuple[List[Position], float]:
        """Fetch Binance positions and USDC balance in one go"""
        positions = []
        usdc_bal = 0.0
        try:
            # We can't easily get all balances in one call without parsing a huge list, 
            # but getting the specific assets we trade is fast.
            for asset in ['SOL', 'BTC', 'ETH', 'AVAX', 'DOGE', 'XRP', 'USDC']:
                bal = self.binance.get_free_balance(asset)
                if asset == 'USDC':
                    usdc_bal = bal
                    continue
                
                if bal > 0.00001:
                    try:
                        t = self.binance.get_ticker_price(f'{asset}USDC')
                        price = float(t.get('price', 0)) if t else 0
                        val = bal * price
                        if val > 1:
                            with self.lock:
                                entry = self.entries.get(f'binance_{asset}', price)
                            positions.append(Position(asset, 'binance', bal, entry, price))
                    except:
                        pass
        except Exception as e:
            # self.log(f"Binance fetch error: {e}")
            pass
        return positions, usdc_bal

    def get_alpaca_data(self) -> Tuple[List[Position], float]:
        """Fetch Alpaca positions and cash"""
        positions = []
        cash_bal = 0.0
        try:
            # Parallelize account and positions
            acc = self.alpaca.get_account()
            cash_bal = float(acc.get('cash', 0))
            
            poss = self.alpaca.get_positions()
            for pos in poss:
                try:
                    sym = pos.get('symbol', '').replace('USD', '')
                    qty = float(pos.get('qty', 0))
                    val = float(pos.get('market_value', 0))
                    entry = float(pos.get('avg_entry_price', 0))
                    current = float(pos.get('current_price', 0))
                    if val > 0.5:
                        positions.append(Position(sym, 'alpaca', qty, entry, current))
                except:
                    pass
        except Exception as e:
            pass
        return positions, cash_bal

    def get_kraken_data(self) -> Tuple[List[Position], float]:
        """Fetch Kraken positions and USD/USDC in one call logic"""
        positions = []
        usd_bal = 0.0
        try:
            acct = self.kraken.account()
            for bal in acct.get('balances', []):
                asset = bal.get('asset', '')
                try:
                    free = float(bal.get('free', 0))
                except:
                    continue
                
                if free <= 0:
                    continue
                
                # Check Cash
                if asset in ['USD', 'USDC', 'ZUSD']:
                    usd_bal += free
                    continue
                    
                if asset in ['USDT', 'ZEUR', 'EUR']:
                    continue # Skip other fiats for now or treat as cash?
                    
                # It's a crypto asset
                if free > 0.00001:
                    try:
                        # Price check
                        pair = f'{asset}USD'
                        ticker = self.kraken.get_ticker(pair)
                        price = float(ticker.get('price', 0))
                        
                        val = free * price
                        if val > 1:
                            with self.lock:
                                entry = self.entries.get(f'kraken_{asset}', price)
                            positions.append(Position(asset, 'kraken', free, entry, price))
                    except:
                        pass
        except Exception as e:
            pass
        return positions, usd_bal

    def find_best_buy(self, platform: str) -> tuple:
        """Find best asset to buy based on momentum"""
        # We use Binance data for momentum across all platforms typically
        pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC', 'AVAXUSDC', 'DOGEUSDC']
        best, best_ch = None, -99
        
        # This could be cached or fetched once per cycle!
        # For now, let's just do it.
        try:
            for pair in pairs:
                try:
                    t = self.binance.get_24h_ticker(pair)
                    ch = float(t.get('priceChangePercent', 0))
                    if ch > best_ch:
                        best, best_ch = pair, ch
                except:
                    pass
        except:
            pass
            
        if platform == 'binance':
            return best, best_ch
        else:
            # Map back to platform specific symbols
            if best:
                sym = best.replace('USDC', '')
                if platform == 'alpaca':
                    return f'{sym}USD', best_ch
                elif platform == 'kraken':
                    return f'{sym}USD', best_ch # Kraken usually uses Append USD
        return None, -99

    def execute_trade(self, platform: str, action: str, **kwargs) -> bool:
        """Unified execution wrapper"""
        try:
            if platform == 'binance':
                if action == 'SELL':
                    return self.binance.place_market_order(kwargs['symbol'], 'SELL', quantity=kwargs['qty'])
                elif action == 'BUY':
                    return self.binance.place_market_order(kwargs['symbol'], 'BUY', quote_qty=kwargs['amount'])
            
            elif platform == 'alpaca':
                if action == 'SELL':
                    return self.alpaca.place_order(kwargs['symbol'], kwargs['qty'], 'sell', 'market', 'ioc')
                elif action == 'BUY':
                    return self.alpaca.place_order(kwargs['symbol'], kwargs['qty'], 'buy', 'market', 'ioc')
            
            elif platform == 'kraken':
                if action == 'SELL':
                    return self.kraken.place_market_order(kwargs['symbol'], 'sell', quantity=kwargs['qty'])
                elif action == 'BUY':
                    return self.kraken.place_market_order(kwargs['symbol'], 'buy', quote_qty=kwargs['amount'])
                    
        except Exception as e:
            self.log(f"Execution error on {platform}: {e}")
            return None
        return None

    def process_profit_taking(self, pos: Position):
        """Take profit and rotate logic"""
        if pos.pnl_pct < self.min_profit_pct:
            return

        self.log(f"📤 {pos.platform.upper()} SELL {pos.asset} @ ${pos.current_price:.2f} ({pos.pnl_pct:+.2f}%)")
        
        # SELL
        res = None
        pair = ''
        if pos.platform == 'binance':
            pair = f'{pos.asset}USDC'
            res = self.execute_trade('binance', 'SELL', symbol=pair, qty=pos.qty * 0.999)
        elif pos.platform == 'alpaca':
            pair = f'{pos.asset}USD'
            res = self.execute_trade('alpaca', 'SELL', symbol=pair, qty=pos.qty)
        elif pos.platform == 'kraken':
            pair = f'{pos.asset}USD'
            res = self.execute_trade('kraken', 'SELL', symbol=pair, qty=pos.qty * 0.999)

        # Check success
        success = False
        if res:
             # Simplify check - different clients return different dicts
             if pos.platform == 'binance' and (res.get('status') == 'FILLED' or 'orderId' in res): success = True
             elif pos.platform == 'alpaca' and res.get('status') in ['filled', 'accepted', 'new']: success = True
             elif pos.platform == 'kraken' and (res.get('txid') or 'dryRun' in res): success = True
        
        if success:
            profit = pos.value * (pos.pnl_pct / 100)
            self.total_profit += profit
            self.trades_taken += 1
            self.log(f"   ✅ SOLD! +${profit:.4f}")
            
            # Fast rotation - don't sleep too long
            # time.sleep(0.2) 
            
            # BUY NEXT BEST
            # We need to know how much cash we have now. 
            # Doing a full fetch is slow. Estimate proceeds?
            proceeds = pos.value # Roughly
            
            if proceeds > 2: # Min threshold
                best, ch = self.find_best_buy(pos.platform)
                if best:
                     asset_buy = best.replace('USDC', '').replace('USD', '')
                     self.log(f"   📥 BUY {best} ({ch:+.1f}%)")
                     
                     buy_res = None
                     if pos.platform == 'binance':
                         buy_res = self.execute_trade('binance', 'BUY', symbol=best, amount=proceeds * 0.98)
                     elif pos.platform == 'alpaca':
                         # Need price to calc qty
                         try:
                             quotes = self.alpaca.get_latest_crypto_quotes([best])
                             price = float(quotes[best].get('ap', 0))
                             qty = (proceeds * 0.95) / price
                             buy_res = self.execute_trade('alpaca', 'BUY', symbol=best, qty=qty)
                         except: pass
                     elif pos.platform == 'kraken':
                         buy_res = self.execute_trade('kraken', 'BUY', symbol=best, amount=proceeds * 0.95)
                         
                     # Record entry
                     if buy_res:
                         # We need to fetch the new price to record entry
                         # Or just use the ticker price we likely used to decide
                         # For now, quick fetch
                         new_entry = 0
                         try:
                             if pos.platform == 'binance':
                                 t = self.binance.get_ticker_price(best)
                                 new_entry = float(t.get('price', 0))
                                 self.log(f"   ✅ BOUGHT {asset_buy}")
                             elif pos.platform == 'kraken':
                                 t = self.kraken.get_ticker(best)
                                 new_entry = float(t.get('price', 0))
                                 self.log(f"   ✅ BOUGHT {asset_buy}")
                             elif pos.platform == 'alpaca':
                                 self.log(f"   ✅ BOUGHT")
                                 # Alpaca entry is async, hard to get immediately without trade id
                         except: pass
                         
                         if new_entry > 0:
                             with self.lock:
                                key = f'{pos.platform}_{asset_buy}'
                                self.entries[key] = new_entry

    def deploy_idle_cash(self, platform: str, amount: float):
        if amount <= 2: return # Too small
        
        # Check if we should deploy? Always yes in Turbo mode
        best, ch = self.find_best_buy(platform)
        if best and ch > 0: # Only if positive momentum? OR just best available?
             self.log(f"💵 {platform.upper()}: Deploying ${amount:.2f} → {best} ({ch:+.1f}%)")
             
             if platform == 'binance':
                 asset = best.replace('USDC', '')
                 r = self.execute_trade('binance', 'BUY', symbol=best, amount=amount * 0.95)
                 if r:
                     t = self.binance.get_ticker_price(best)
                     with self.lock: self.entries[f'binance_{asset}'] = float(t.get('price', 0))
                     self.log(f"   ✅ Deployed")
                     
             elif platform == 'kraken':
                 asset = best.replace('USD', '')
                 r = self.execute_trade('kraken', 'BUY', symbol=best, amount=amount * 0.95)
                 if r:
                     t = self.kraken.get_ticker(best)
                     with self.lock: self.entries[f'kraken_{asset}'] = float(t.get('price', 0))
                     self.log(f"   ✅ Deployed")
            
             elif platform == 'alpaca':
                 try:
                     quotes = self.alpaca.get_latest_crypto_quotes([best])
                     price = float(quotes[best].get('ap', 0))
                     qty = (amount * 0.95) / price
                     r = self.execute_trade('alpaca', 'BUY', symbol=best, qty=qty)
                     if r: self.log(f"   ✅ Deployed")
                 except: pass

    def run_cycle(self):
        # Parallel fetch
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_bin = executor.submit(self.get_binance_data)
            future_alp = executor.submit(self.get_alpaca_data)
            future_krk = executor.submit(self.get_kraken_data)
            
            bin_pos, bin_cash = future_bin.result()
            alp_pos, alp_cash = future_alp.result()
            krk_pos, krk_cash = future_krk.result()
            
        # Consolidate
        all_positions = bin_pos + alp_pos + krk_pos
        
        # Process profits (Sequential to avoid weird console interleaving/race conditions, but doing it fast)
        for pos in all_positions:
            self.process_profit_taking(pos)
            
        # Deploy idle cash
        self.deploy_idle_cash('binance', bin_cash)
        self.deploy_idle_cash('alpaca', alp_cash)
        self.deploy_idle_cash('kraken', krk_cash)
        
        return all_positions, (bin_cash, alp_cash, krk_cash)

    def print_status(self, positions, cash_tuple):
        bin_cash, alp_cash, krk_cash = cash_tuple
        total = bin_cash + alp_cash + krk_cash
        
        # Group by platform
        by_plat = {'binance': [], 'alpaca': [], 'kraken': []}
        for p in positions:
            by_plat[p.platform].append(p)
            total += p.value

        self.log(f"--- STATUS --- Trades: {self.trades_taken} | Profit: ${self.total_profit:.4f} | Total Equity: ${total:.2f}")
        # Compact print
        for plat, poss in by_plat.items():
            if not poss and ((plat=='binance' and bin_cash<1) or (plat=='alpaca' and alp_cash<1) or (plat=='kraken' and krk_cash<1)):
                continue
            line = f"{plat.upper()}: "
            items = []
            for p in poss:
                icon = '🟢' if p.pnl_pct >= 0 else '🔴'
                items.append(f"{icon}{p.asset} {p.pnl_pct:+.1f}%")
            
            cash_val = 0
            if plat == 'binance': cash_val = bin_cash
            elif plat == 'alpaca': cash_val = alp_cash
            elif plat == 'kraken': cash_val = krk_cash
            
            if cash_val > 1:
                items.append(f"💵 ${cash_val:.0f}")
                
            self.log(line + " | ".join(items))

    def run(self):
        print("🔥 GAIA TURBO STARTED - FAST MODE 🔥")
        
        cycle = 0
        while True:
            try:
                start_time = time.time()
                positions, cash = self.run_cycle()
                duration = time.time() - start_time
                
                if cycle % 10 == 0:
                    self.print_status(positions, cash)
                
                cycle += 1
                
                # Adaptive sleep - if cycle took long, don't sleep
                sleep_time = max(0.2, 1.0 - duration)
                # print(f"Cycle took {duration:.2f}s, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("STOPPED")
                break
            except Exception as e:
                self.log(f"CRITICAL LOOP ERROR: {e}")
                time.sleep(1)

if __name__ == "__main__":
    t = GaiaTurboTrader()
    t.run()
