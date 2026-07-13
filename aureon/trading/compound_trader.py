#!/usr/bin/env python3
"""
⚡ AUREON COMPOUND TRADER ⚡
Executes trades and compounds profits automatically.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
import time
import json
from datetime import datetime

FEE = 0.001
GBP = 0.79

class CompoundTrader:
    def __init__(self):
        self.client = get_binance_client()
        self.positions = {}  # symbol -> {entry, qty, target, stop}
        self.trades_completed = 0
        self.total_profit = 0.0
        self.starting_capital = 0.0
        
    def get_balances(self):
        """Get current balances"""
        acct = self.client.account()
        balances = {}
        for b in acct['balances']:
            free = float(b['free'])
            if free > 0:
                balances[b['asset']] = free
        return balances
    
    def get_usdc_balance(self):
        return self.get_balances().get('USDC', 0)
    
    def find_opportunity(self, pairs):
        """Find best trading opportunity"""
        best = None
        
        for sym in pairs:
            try:
                resp = self.client.session.get(
                    f'{self.client.base}/api/v3/ticker/24hr',
                    params={'symbol': sym}, timeout=2
                )
                t = resp.json()
                
                price = float(t['lastPrice'])
                high = float(t['highPrice'])
                low = float(t['lowPrice'])
                
                if high == low:
                    continue
                    
                position = (price - low) / (high - low)
                range_pct = (high - low) / low * 100
                
                # BUY setup: price near low of range
                if position < 0.35 and range_pct > 2:
                    target = low + (high - low) * 0.618
                    profit_pct = ((target - price) / price - FEE * 2) * 100
                    
                    if profit_pct > 0.5:
                        if not best or profit_pct > best['profit_pct']:
                            best = {
                                'symbol': sym,
                                'side': 'BUY',
                                'price': price,
                                'target': target,
                                'stop': price * 0.98,
                                'profit_pct': profit_pct
                            }
                
                # SELL setup: price near high of range
                elif position > 0.65 and range_pct > 2:
                    target = low + (high - low) * 0.382
                    profit_pct = ((price - target) / price - FEE * 2) * 100
                    
                    if profit_pct > 0.5:
                        if not best or profit_pct > best['profit_pct']:
                            best = {
                                'symbol': sym,
                                'side': 'SELL',
                                'price': price,
                                'target': target,
                                'stop': price * 1.02,
                                'profit_pct': profit_pct
                            }
            except:
                pass
        
        return best
    
    def open_position(self, opportunity, size_usdc):
        """Open a new position"""
        sym = opportunity['symbol']
        side = opportunity['side']
        
        print(f"\n🎯 Opening {side} {sym}")
        print(f"   Size: ${size_usdc:.2f}")
        print(f"   Entry: ${opportunity['price']:.4f}")
        print(f"   Target: ${opportunity['target']:.4f} ({opportunity['profit_pct']:.2f}%)")
        
        try:
            if side == 'BUY':
                result = self.client.place_market_order(sym, 'BUY', quote_qty=size_usdc)
            else:
                # For SELL, we need to have the asset first
                result = self.client.place_market_order(sym, 'SELL', quote_qty=size_usdc)
            
            if result.get('status') == 'FILLED':
                qty = float(result['executedQty'])
                avg_price = float(result['cummulativeQuoteQty']) / qty if qty > 0 else opportunity['price']
                
                self.positions[sym] = {
                    'side': side,
                    'entry': avg_price,
                    'qty': qty,
                    'target': opportunity['target'],
                    'stop': opportunity['stop'],
                    'open_time': time.time()
                }
                
                print(f"   ✅ FILLED: {qty:.6f} @ ${avg_price:.4f}")
                return True
            else:
                print(f"   ❌ Order not filled: {result}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def check_positions(self):
        """Check all open positions for exit signals"""
        for sym in list(self.positions.keys()):
            pos = self.positions[sym]
            
            try:
                ticker = self.client.best_price(sym)
                current_price = float(ticker['price'])
                
                should_close = False
                reason = ""
                
                if pos['side'] == 'BUY':
                    if current_price >= pos['target']:
                        should_close = True
                        reason = "TARGET HIT"
                    elif current_price <= pos['stop']:
                        should_close = True
                        reason = "STOP HIT"
                else:  # SELL
                    if current_price <= pos['target']:
                        should_close = True
                        reason = "TARGET HIT"
                    elif current_price >= pos['stop']:
                        should_close = True
                        reason = "STOP HIT"
                
                if should_close:
                    self.close_position(sym, current_price, reason)
                else:
                    pnl = (current_price - pos['entry']) / pos['entry'] * 100
                    if pos['side'] == 'SELL':
                        pnl = -pnl
                    print(f"   📊 {sym}: ${current_price:.4f} ({pnl:+.2f}%)")
                    
            except Exception as e:
                print(f"   ⚠️ Error checking {sym}: {e}")
    
    def close_position(self, symbol, price, reason):
        """Close a position"""
        pos = self.positions[symbol]
        
        try:
            if pos['side'] == 'BUY':
                # Sell the asset
                result = self.client.place_market_order(symbol, 'SELL', quantity=pos['qty'])
            else:
                # Buy back
                quote_qty = pos['qty'] * price
                result = self.client.place_market_order(symbol, 'BUY', quote_qty=quote_qty)
            
            if result.get('status') == 'FILLED':
                exit_price = float(result['cummulativeQuoteQty']) / float(result['executedQty'])
                
                if pos['side'] == 'BUY':
                    pnl_pct = (exit_price - pos['entry']) / pos['entry']
                else:
                    pnl_pct = (pos['entry'] - exit_price) / pos['entry']
                
                pnl_usdc = pos['qty'] * pos['entry'] * pnl_pct
                pnl_gbp = pnl_usdc * GBP
                
                print(f"\n{'✅' if pnl_usdc > 0 else '❌'} CLOSED {pos['side']} {symbol} - {reason}")
                print(f"   Entry: ${pos['entry']:.4f}")
                print(f"   Exit: ${exit_price:.4f}")
                print(f"   P&L: ${pnl_usdc:.4f} (£{pnl_gbp:.4f})")
                
                self.trades_completed += 1
                self.total_profit += pnl_usdc
                
                del self.positions[symbol]
                return True
                
        except Exception as e:
            print(f"   ❌ Error closing {symbol}: {e}")
            return False
    
    def run(self, pairs, trade_size_pct=0.25, check_interval=5, max_trades=20):
        """Run the compound trading loop"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    ⚡ AUREON COMPOUND TRADER ⚡                                ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self.starting_capital = self.get_usdc_balance()
        print(f"💰 Starting Capital: ${self.starting_capital:.2f}")
        print(f"📊 Trade Size: {trade_size_pct*100:.0f}% of capital")
        print(f"🎯 Target Trades: {max_trades}")
        print(f"⏱️ Check Interval: {check_interval}s")
        print()
        print("=" * 60)
        
        while self.trades_completed < max_trades:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] Cycle {self.trades_completed + 1}/{max_trades}")
            
            # Check existing positions
            if self.positions:
                print("   Checking positions...")
                self.check_positions()
            
            # Look for new opportunities if we have capital
            usdc = self.get_usdc_balance()
            trade_size = usdc * trade_size_pct
            
            if trade_size >= 10 and len(self.positions) < 3:  # Max 3 concurrent
                opp = self.find_opportunity(pairs)
                if opp and opp['symbol'] not in self.positions:
                    self.open_position(opp, trade_size)
            
            time.sleep(check_interval)
        
        # Final report
        self.print_report()
    
    def print_report(self):
        final_capital = self.get_usdc_balance()
        total_growth = (final_capital / self.starting_capital - 1) * 100 if self.starting_capital > 0 else 0
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         SESSION COMPLETE                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Trades Completed:    {self.trades_completed:>6}                             ║
║   Starting Capital:    ${self.starting_capital:>10.2f}                        ║
║   Final Capital:       ${final_capital:>10.2f}                                ║
║   Total Profit:        ${self.total_profit:>10.2f}                            ║
║   Growth:              {total_growth:>10.2f}%                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=float, default=0.25, help='Trade size as % of capital')
    parser.add_argument('--interval', type=int, default=10, help='Check interval in seconds')
    parser.add_argument('--trades', type=int, default=10, help='Max trades to complete')
    args = parser.parse_args()
    
    trader = CompoundTrader()
    
    # USDC pairs (what you can trade)
    pairs = ['SOLUSDC', 'XRPUSDC', 'ADAUSDC', 'DOGEUSDC', 'AVAXUSDC', 
             'ETHUSDC', 'BNBUSDC', 'BTCUSDC']
    
    trader.run(pairs, trade_size_pct=args.size, check_interval=args.interval, max_trades=args.trades)
