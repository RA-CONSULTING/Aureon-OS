#!/usr/bin/env python3
"""
🎯 QUICK SNIPER - FAST PROFIT EXECUTION
No overthinking, just profit!
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping - causes Windows exit errors
    except Exception:
        pass

import time
import json
from datetime import datetime

# Load Kraken client
from kraken_client import KrakenClient

def load_kraken():
    """Load Kraken with API keys."""
    from dotenv import load_dotenv
    load_dotenv()
    return KrakenClient()  # Loads keys from env automatically

def get_best_breakout(kraken):
    """Find the BEST breakout opportunity RIGHT NOW."""
    print("\n🔍 SCANNING FOR BREAKOUTS...")
    
    tickers = kraken.get_24h_tickers()
    if not tickers:
        print("❌ No ticker data")
        return None
    
    # Convert list to dict if needed
    if isinstance(tickers, list):
        tickers_dict = {}
        for t in tickers:
            if isinstance(t, dict) and 'symbol' in t:
                tickers_dict[t['symbol']] = t
        tickers = tickers_dict
    
    # Find best opportunities
    opportunities = []
    
    for symbol, data in tickers.items():
        # Skip non-USD pairs
        if not symbol.endswith('USD') and not symbol.endswith('USDC'):
            continue
        
        # Skip stablecoins
        base = symbol.replace('USDC', '').replace('USD', '')
        if base in ['USDT', 'USDC', 'DAI', 'TUSD', 'ZUSD', 'PAX', 'BUSD']:
            continue
        
        try:
            change = float(data.get('priceChangePercent', 0))
            volume = float(data.get('quoteVolume', 0))
            price = float(data.get('lastPrice', 0))
            
            # Looking for:
            # 1. Strong upward momentum (+5% to +50%)
            # 2. Good volume (> $10k)
            # 3. Not too expensive (< $100 so we can get decent qty)
            
            if 5 < change < 50 and volume > 10000 and 0.0001 < price < 100:
                score = change * (volume / 100000)  # Simple momentum * volume score
                opportunities.append({
                    'symbol': symbol,
                    'base': base,
                    'price': price,
                    'change': change,
                    'volume': volume,
                    'score': score
                })
        except:
            continue
    
    # Sort by score
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n🎯 TOP BREAKOUTS:")
    for i, opp in enumerate(opportunities[:10]):
        print(f"   {i+1}. {opp['symbol']:12} +{opp['change']:.1f}% | Vol: ${opp['volume']:,.0f} | Price: ${opp['price']:.4f}")
    
    return opportunities[:10] if opportunities else None

def execute_buy(kraken, symbol, quote_amount):
    """Execute a BUY order."""
    print(f"\n🚀 EXECUTING BUY: {symbol} with ${quote_amount:.2f}")
    
    try:
        result = kraken.place_market_order(symbol, 'buy', quote_qty=quote_amount)
        print(f"✅ ORDER RESULT: {result}")
        return result
    except Exception as e:
        print(f"❌ Order failed: {e}")
        return None

def main():
    print("=" * 60)
    print("🎯 QUICK SNIPER - PULL THIS OFF NOW!")
    print("=" * 60)
    
    kraken = load_kraken()
    
    # Get balances
    balances = kraken.get_account_balance()
    print(f"\n💰 KRAKEN BALANCES:")
    
    usdc_balance = 0
    tusd_balance = 0
    melania_balance = 0
    
    for asset, amount in balances.items():
        if float(amount) > 0.01:
            print(f"   {asset}: {float(amount):.4f}")
            if asset == 'USDC':
                usdc_balance = float(amount)
            elif asset == 'TUSD':
                tusd_balance = float(amount)
            elif asset == 'MELANIA':
                melania_balance = float(amount)
    
    # Check MELANIA position first
    tickers = kraken.get_24h_tickers()
    
    # Convert list to dict if needed
    if isinstance(tickers, list):
        tickers_dict = {}
        for t in tickers:
            if isinstance(t, dict) and 'symbol' in t:
                tickers_dict[t['symbol']] = t
        tickers = tickers_dict
    
    melania_ticker = tickers.get('MELANIAUSDC') or tickers.get('MELANIAUSD')
    
    if melania_ticker and melania_balance > 0:
        current_price = float(melania_ticker.get('lastPrice', 0))
        entry_price = 0.1515  # Your entry
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        value = melania_balance * current_price
        
        print(f"\n📊 MELANIA POSITION:")
        print(f"   Amount: {melania_balance:.2f}")
        print(f"   Entry: ${entry_price:.4f}")
        print(f"   Current: ${current_price:.4f}")
        print(f"   PnL: {pnl_pct:+.2f}%")
        print(f"   Value: ${value:.2f}")
        
        # If profitable, SELL IT!
        if pnl_pct >= 0.5:  # 0.5% profit target (lower for speed)
            print(f"\n🎯💰 PROFIT TARGET HIT! SELLING MELANIA...")
            try:
                # Try USDC pair first
                result = kraken.place_market_order('MELANIAUSDC', 'sell', base_qty=melania_balance)
                print(f"✅ SOLD: {result}")
                
                # Refresh balances
                time.sleep(2)
                balances = kraken.get_account_balance()
                usdc_balance = float(balances.get('USDC', 0))
                print(f"✅ New USDC balance: ${usdc_balance:.2f}")
            except Exception as e:
                print(f"❌ Sell failed: {e}")
    
    # Now find next opportunity
    print("\n" + "=" * 60)
    print("🔍 HUNTING NEXT OPPORTUNITY...")
    print("=" * 60)
    
    opportunities = get_best_breakout(kraken)
    
    if not opportunities:
        print("❌ No good opportunities found")
        return
    
    # Available to trade
    available = usdc_balance
    if tusd_balance > 1:
        # Convert TUSD to USDC first
        print(f"\n💱 Converting TUSD (${tusd_balance:.2f}) to USDC...")
        try:
            result = kraken.place_market_order('TUSDUSD', 'sell', base_qty=tusd_balance)
            print(f"✅ Converted: {result}")
            time.sleep(2)
            balances = kraken.get_account_balance()
            available = float(balances.get('USDC', 0)) + float(balances.get('USD', 0))
        except Exception as e:
            print(f"⚠️ TUSD conversion failed: {e}")
    
    print(f"\n💵 AVAILABLE TO TRADE: ${available:.2f}")
    
    if available < 1:
        print("❌ Not enough funds to trade")
        return
    
    # Execute on TOP opportunity
    for opp in opportunities:
        symbol = opp['symbol']
        
        # Use 90% of available (keep some buffer)
        trade_amount = available * 0.9
        
        print(f"\n🎯 TARGETING: {symbol}")
        print(f"   24h Change: +{opp['change']:.1f}%")
        print(f"   Volume: ${opp['volume']:,.0f}")
        print(f"   Trade Amount: ${trade_amount:.2f}")
        
        # Try to execute
        try:
            # Determine quote currency
            if symbol.endswith('USDC'):
                result = kraken.place_market_order(symbol, 'buy', quote_qty=trade_amount)
            else:
                result = kraken.place_market_order(symbol, 'buy', quote_qty=trade_amount)
            
            if result and 'error' not in str(result).lower():
                print(f"\n✅✅✅ EXECUTED! {result}")
                
                # Save position
                position = {
                    'symbol': symbol,
                    'side': 'buy',
                    'entry_time': datetime.now().isoformat(),
                    'amount_usd': trade_amount,
                    'entry_price': opp['price'],
                    'change_at_entry': opp['change']
                }
                
                with open('quick_sniper_position.json', 'w') as f:
                    json.dump(position, f, indent=2)
                
                print(f"💾 Position saved to quick_sniper_position.json")
                return
            else:
                print(f"⚠️ Order issue: {result}")
                continue
                
        except Exception as e:
            print(f"⚠️ Failed on {symbol}: {e}")
            continue
    
    print("\n❌ Could not execute on any opportunity")

if __name__ == '__main__':
    main()
