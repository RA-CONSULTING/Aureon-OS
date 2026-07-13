#!/usr/bin/env python3
"""
🌊 WAVE RIDER AUTO - Continuous Market Riding System 🌊

This system:
1. Monitors active positions
2. Auto-exits at target or stop
3. Finds new opportunities when flat
4. NEVER stops riding the waves

The market is ALWAYS moving. We ride it.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import requests
import time
import os
from datetime import datetime, timezone
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

class WaveRiderAuto:
    """Continuous wave riding system"""
    
    def __init__(self, live_mode: bool = True):
        self.binance = get_binance_client()
        self.live_mode = live_mode
        self.position_file = 'active_position.json'
        self.trade_history_file = 'wave_rider_history.json'
        self.total_profit = 0.0
        
        # Settings
        self.min_trade_size = 5.0  # Minimum $5 to trade
        self.target_pct = 5.0  # 5% profit target
        self.stop_pct = -3.0  # 3% stop loss
        self.min_score = 50  # Minimum opportunity score
        
        print("🌊 WAVE RIDER AUTO INITIALIZED")
        self._load_history()
        
    def _load_history(self):
        """Load trade history"""
        try:
            with open(self.trade_history_file, 'r') as f:
                history = json.load(f)
                self.total_profit = history.get('total_profit', 0)
                print(f"   📊 Loaded history: ${self.total_profit:+.2f} total profit")
        except:
            self.total_profit = 0
            
    def _save_history(self, trade: dict):
        """Save trade to history"""
        try:
            try:
                with open(self.trade_history_file, 'r') as f:
                    history = json.load(f)
            except:
                history = {'trades': [], 'total_profit': 0}
            
            history['trades'].append(trade)
            history['total_profit'] = self.total_profit
            history['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            with open(self.trade_history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ Could not save history: {e}")
    
    def get_position(self) -> dict:
        """Get current position if any"""
        try:
            if os.path.exists(self.position_file):
                with open(self.position_file, 'r') as f:
                    pos = json.load(f)
                    if pos.get('status') == 'open':
                        return pos
        except:
            pass
        return None
    
    def save_position(self, position: dict):
        """Save position to file"""
        with open(self.position_file, 'w') as f:
            json.dump(position, f, indent=2)
    
    def clear_position(self):
        """Clear position file"""
        if os.path.exists(self.position_file):
            os.remove(self.position_file)
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            resp = requests.get(url, timeout=10)
            return float(resp.json()['price'])
        except:
            return 0
    
    def find_opportunities(self) -> list:
        """Find trading opportunities"""
        try:
            resp = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=30)
            all_tickers = resp.json()
            
            opportunities = []
            for t in all_tickers:
                try:
                    symbol = t['symbol']
                    if not symbol.endswith('USDC'):
                        continue
                    
                    high = float(t['highPrice'])
                    low = float(t['lowPrice'])
                    last = float(t['lastPrice'])
                    change = float(t['priceChangePercent'])
                    volume = float(t['quoteVolume'])
                    
                    if last <= 0 or high <= low or volume < 100000:
                        continue
                    
                    position_in_range = (last - low) / (high - low) * 100
                    potential_up = (high - last) / last * 100
                    
                    # Score: near bottom + volume + not crashing + upside
                    score = 0
                    if position_in_range < 30:
                        score += (30 - position_in_range) * 2
                    if volume > 500000:
                        score += 20
                    if change > -15:
                        score += 10
                    if potential_up > 5:
                        score += min(potential_up, 30)
                    
                    if score >= self.min_score:
                        opportunities.append({
                            'symbol': symbol,
                            'position': position_in_range,
                            'change': change,
                            'volume': volume,
                            'potential': potential_up,
                            'price': last,
                            'score': score
                        })
                except:
                    pass
            
            return sorted(opportunities, key=lambda x: -x['score'])[:10]
        except Exception as e:
            print(f"   ⚠️ Error finding opportunities: {e}")
            return []
    
    def open_position(self, opportunity: dict, capital: float) -> bool:
        """Open a new position"""
        symbol = opportunity['symbol']
        print(f"\n⚡ OPENING POSITION: {symbol}")
        
        trade_amount = min(capital * 0.95, capital)
        
        try:
            result = self.binance.place_market_order(symbol, 'BUY', quote_qty=trade_amount)
            
            if result.get('rejected'):
                print(f"   ❌ Rejected: {result.get('reason')}")
                return False
            
            if result.get('status') == 'FILLED':
                fills = result.get('fills', [])
                if fills:
                    avg_price = sum(float(f['price']) * float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills)
                    qty = sum(float(f['qty']) for f in fills)
                    
                    position = {
                        'symbol': symbol,
                        'base_asset': symbol.replace('USDC', ''),
                        'entry_price': avg_price,
                        'quantity': qty,
                        'amount_usdc': trade_amount,
                        'target_pct': self.target_pct,
                        'target_price': avg_price * (1 + self.target_pct/100),
                        'stop_pct': self.stop_pct,
                        'stop_price': avg_price * (1 + self.stop_pct/100),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'status': 'open'
                    }
                    
                    self.save_position(position)
                    
                    print(f"   ✅ Bought {qty:.4f} {position['base_asset']} at ${avg_price:.6f}")
                    print(f"   🎯 Target: ${position['target_price']:.6f}")
                    print(f"   🛡️ Stop: ${position['stop_price']:.6f}")
                    return True
            
            print(f"   ⚠️ Unexpected result: {result}")
            return False
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def close_position(self, position: dict, reason: str) -> float:
        """Close current position"""
        symbol = position['symbol']
        base_asset = position['base_asset']
        
        print(f"\n⚡ CLOSING POSITION: {symbol} ({reason})")
        
        try:
            balance = self.binance.get_free_balance(base_asset)
            if not balance or balance <= 0:
                print(f"   ⚠️ No balance to sell")
                self.clear_position()
                return 0
            
            result = self.binance.place_market_order(symbol, 'SELL', quantity=balance)
            
            if result.get('status') == 'FILLED':
                fills = result.get('fills', [])
                if fills:
                    exit_price = sum(float(f['price']) * float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills)
                    pnl = balance * (exit_price - position['entry_price'])
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
                    
                    self.total_profit += pnl
                    
                    print(f"   ✅ Sold {balance:.4f} at ${exit_price:.6f}")
                    print(f"   💰 P&L: ${pnl:+.4f} ({pnl_pct:+.2f}%)")
                    print(f"   📊 Total profit: ${self.total_profit:+.2f}")
                    
                    # Save to history
                    trade_record = {
                        'symbol': symbol,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': balance,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': reason,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    self._save_history(trade_record)
                    
                    self.clear_position()
                    return pnl
            
            print(f"   ⚠️ Sell result: {result}")
            return 0
            
        except Exception as e:
            print(f"   ❌ Error closing: {e}")
            return 0
    
    def check_position(self, position: dict) -> tuple:
        """Check if position should be closed. Returns (should_close, reason)"""
        current_price = self.get_current_price(position['symbol'])
        if current_price <= 0:
            return False, ""
        
        if current_price >= position['target_price']:
            return True, "🎯 TARGET HIT"
        
        if current_price <= position['stop_price']:
            return True, "🛡️ STOP LOSS"
        
        return False, ""
    
    def run(self, duration_minutes: int = 60):
        """Main loop - ride the waves"""
        print("=" * 70)
        print("🌊 WAVE RIDER AUTO - STARTING")
        print("=" * 70)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        cycle = 0
        
        print(f"\n⏱️ Running for {duration_minutes} minutes")
        print("   Press Ctrl+C to stop\n")
        
        try:
            while time.time() < end_time:
                cycle += 1
                now = datetime.now(timezone.utc).strftime('%H:%M:%S')
                
                print(f"\n{'='*50}")
                print(f"📡 Cycle #{cycle} at {now} UTC")
                
                # Check for existing position
                position = self.get_position()
                
                if position:
                    # Monitor existing position
                    current_price = self.get_current_price(position['symbol'])
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
                    
                    print(f"   📍 Holding {position['base_asset']}: {pnl_pct:+.2f}%")
                    
                    should_close, reason = self.check_position(position)
                    if should_close:
                        self.close_position(position, reason)
                    
                else:
                    # Look for new opportunity
                    usdc_balance = self.binance.get_free_balance('USDC')
                    print(f"   💰 USDC: ${usdc_balance:.2f}")
                    
                    if usdc_balance >= self.min_trade_size:
                        opportunities = self.find_opportunities()
                        
                        if opportunities:
                            print(f"   🔍 Found {len(opportunities)} opportunities")
                            
                            # Try to open position with best opportunities
                            for opp in opportunities[:5]:
                                print(f"   → Trying {opp['symbol']} (score: {opp['score']:.0f})")
                                if self.open_position(opp, usdc_balance):
                                    break
                        else:
                            print("   😴 No good opportunities right now")
                    else:
                        print(f"   ⚠️ Insufficient balance (need ${self.min_trade_size})")
                
                # Wait between cycles
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        print(f"   Cycles: {cycle}")
        print(f"   Duration: {(time.time() - start_time)/60:.1f} minutes")
        print(f"   Total profit: ${self.total_profit:+.2f}")
        
        # Check if we still have a position
        position = self.get_position()
        if position:
            current_price = self.get_current_price(position['symbol'])
            unrealized = position['quantity'] * (current_price - position['entry_price'])
            print(f"   Open position: {position['symbol']} (${unrealized:+.2f} unrealized)")


def main():
    import sys
    
    live_mode = '--live' in sys.argv
    duration = 60  # Default 60 minutes
    
    for arg in sys.argv:
        if arg.startswith('--minutes='):
            duration = int(arg.split('=')[1])
    
    rider = WaveRiderAuto(live_mode=live_mode)
    rider.run(duration_minutes=duration)
    
    print("\n🌊 Wave Rider signing off! See you next wave! 🐝👑")


if __name__ == '__main__':
    main()
