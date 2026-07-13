#!/usr/bin/env python3
"""Calculate total portfolio value in USDT and start trading with existing assets."""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

from aureon.exchanges.binance_client import BinanceClient, get_binance_client
import json

client = get_binance_client()

print("\n" + "="*80)
print("PORTFOLIO VALUATION & TRADING READINESS")
print("="*80)

account = client.account()
balances_with_value = []
total_usdt_value = 0.0

# Get all prices
print("\n📊 Calculating portfolio value...\n")

for bal in account['balances']:
    free = float(bal['free'])
    locked = float(bal['locked'])
    total = free + locked
    
    if total > 0:
        asset = bal['asset']
        
        # Convert to USDT value
        if asset == 'USDT':
            usdt_value = total
        elif asset in ['LDUSDC', 'USDC', 'BUSD']:
            usdt_value = total  # 1:1 with USDT
        else:
            try:
                symbol = f"{asset}USDT"
                price_data = client.best_price(symbol)
                price = float(price_data['price'])
                usdt_value = total * price
            except:
                # Try inverse pair or skip
                try:
                    symbol = f"USDT{asset}"
                    price_data = client.best_price(symbol)
                    price = float(price_data['price'])
                    usdt_value = total / price if price > 0 else 0
                except:
                    usdt_value = 0
        
        if usdt_value > 0:
            balances_with_value.append({
                'asset': asset,
                'free': free,
                'locked': locked,
                'total': total,
                'usdt_value': usdt_value
            })
            total_usdt_value += usdt_value

# Sort by USDT value
balances_with_value.sort(key=lambda x: x['usdt_value'], reverse=True)

print(f"{'Asset':<10} {'Free':<15} {'Locked':<15} {'Total':<15} {'USDT Value':<15}")
print("-"*80)

for item in balances_with_value:
    print(f"{item['asset']:<10} {item['free']:<15.8f} {item['locked']:<15.8f} {item['total']:<15.8f} ${item['usdt_value']:<15.2f}")

print("-"*80)
print(f"{'TOTAL PORTFOLIO VALUE':<55} ${total_usdt_value:<15.2f}")
print("="*80)

print(f"\n💰 Total Portfolio: ${total_usdt_value:.2f} USDT equivalent")
print(f"🎯 Tradeable Capital: ${total_usdt_value:.2f}")
print(f"📊 Number of Assets: {len(balances_with_value)}")

# Trading readiness
if total_usdt_value >= 10:
    print(f"\n✅ READY TO TRADE!")
    print(f"   Minimum notional: $10 USDT ✓")
    print(f"   Recommended strategy:")
    print(f"   - Convert small altcoins to USDT for easier trading")
    print(f"   - Or trade pairs directly (e.g., BTCUSDT, ETHUSDT, etc.)")
    print(f"   - Risk 2% per trade = ${total_usdt_value * 0.02:.2f} per position")
else:
    print(f"\n⚠️  Portfolio < $10 minimum for Binance spot trading")
    print(f"   Need to deposit more or consolidate assets")

print("\n" + "="*80 + "\n")
