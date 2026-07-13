#!/usr/bin/env python3
"""Convert portfolio assets to USDT for trading"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from dotenv import load_dotenv

load_dotenv()

if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
    print("❌ Set CONFIRM_LIVE=yes to execute conversions")
    sys.exit(1)

client = get_binance_client()
account = client.account()

# Get all non-zero balances
balances = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0.001}

print(f"\n💼 Current Holdings:")
for asset, amount in balances.items():
    print(f"  {asset}: {amount:.6f}")

# Assets to keep some of (don't convert 100%)
KEEP_ASSETS = {'BTC', 'ETH', 'BNB'}
# Assets to convert entirely
CONVERT_ASSETS = {'LINK', 'ADA', 'DOT', 'DOGE', 'XRP', 'SOL', 'AVAX', 'LDUSDC'}

print(f"\n🔄 Converting to USDT...")

conversions = []
for asset in CONVERT_ASSETS:
    if asset not in balances or balances[asset] < 0.001:
        continue
        
    amount = balances[asset]
    symbol = f"{asset}USDT"
    
    try:
        # Check if pair exists
        info = client.exchange_info()
        pair_exists = any(s['symbol'] == symbol and s['status'] == 'TRADING' for s in info['symbols'])
        
        if not pair_exists:
            print(f"  ⚠️  {symbol} pair not tradeable, skipping...")
            continue
        
        # Get current price
        ticker = client.best_price(symbol)
        price = float(ticker['price'])
        usdt_value = amount * price
        
        # Skip if < $5 USDT value
        if usdt_value < 5.0:
            print(f"  ⏩ {asset}: ${usdt_value:.2f} too small, skipping...")
            continue
        
        print(f"  💰 Converting {amount:.4f} {asset} -> ${usdt_value:.2f} USDT...")
        result = client.place_market_order(symbol, 'SELL', quantity=amount)
        print(f"  ✅ SOLD {asset}: {result.get('executedQty', 'unknown')} @ avg {result.get('fills', [{}])[0].get('price', price)}")
        conversions.append({'asset': asset, 'usdt_value': usdt_value})
        
    except Exception as e:
        print(f"  ❌ Failed to convert {asset}: {e}")

if conversions:
    total_converted = sum(c['usdt_value'] for c in conversions)
    print(f"\n✅ Converted {len(conversions)} assets -> ~${total_converted:.2f} USDT")
    
    # Check new USDT balance
    new_account = client.account()
    usdt_bal = float([b['free'] for b in new_account['balances'] if b['asset'] == 'USDT'][0])
    print(f"💵 New USDT balance: {usdt_bal:.2f} USDT")
else:
    print(f"\n⚠️  No conversions executed")
